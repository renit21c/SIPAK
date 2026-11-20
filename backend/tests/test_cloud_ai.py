import asyncio
import json
import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select
from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models import Audit
from backend.app.services.ai_provider import InferenceConfig, strict_schema, snapshot
from backend.app.services.extraction import infer

FAKE_KEY='test-key-not-a-real-credential'

def cloud(monkeypatch):
    monkeypatch.setattr(settings,'ai_provider','openrouter')
    monkeypatch.setattr(settings,'ai_model','test/model')
    monkeypatch.setattr(settings,'openrouter_api_key',SecretStr(FAKE_KEY))

def mock_http(monkeypatch,handler):
    actual=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:actual(transport=httpx.MockTransport(handler),**kwargs))

def config(authorized=True):
    return InferenceConfig('openrouter','test/model',SecretStr(FAKE_KEY),180,authorized)

def test_schema_requires_all_properties():
    schema=strict_schema()
    def walk(value):
        if isinstance(value,dict):
            if value.get('type')=='object':
                assert value['additionalProperties'] is False
                assert set(value['required'])==set(value['properties'])
            assert 'default' not in value
            for child in value.values(): walk(child)
        elif isinstance(value,list):
            for child in value: walk(child)
    walk(schema)
    assert FAKE_KEY not in repr(config())

def test_adapter_blocks_without_authorization(monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('Network must not be called')
    monkeypatch.setattr(httpx,'AsyncClient',forbidden)
    with pytest.raises(ValueError,match='Persetujuan'):
        asyncio.run(infer([{'page':1,'text':'synthetic test'}],config=config(False)))

def test_openrouter_structured_output(monkeypatch,extracted):
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':extracted.model_dump_json()}}]})
    mock_http(monkeypatch,handler)
    result=asyncio.run(infer([{'page':1,'text':'synthetic test'}],config=config()))
    assert result==extracted and len(requests)==1
    request=requests[0];body=json.loads(request.content)
    assert str(request.url)=='https://openrouter.ai/api/v1/chat/completions'
    assert request.headers['Authorization']=='Bearer '+FAKE_KEY
    assert body['model']=='test/model' and body['response_format']['json_schema']['strict'] is True
    assert body['provider']=={'require_parameters':True,'data_collection':'deny','zdr':True,'allow_fallbacks':False}

@pytest.mark.parametrize('status',[401,402,403,404,429,500])
def test_provider_errors_are_redacted(monkeypatch,status):
    mock_http(monkeypatch,lambda req:httpx.Response(status,json={'error':{'message':FAKE_KEY+' secret document text'}}))
    with pytest.raises(ValueError) as error:
        asyncio.run(infer([{'page':1,'text':'secret document text'}],config=config()))
    assert FAKE_KEY not in str(error.value) and 'secret document text' not in str(error.value)

@pytest.mark.parametrize('content,finish',[('not JSON','stop'),('{}','length'),('{}','content_filter')])
def test_invalid_or_truncated_output_fails(monkeypatch,content,finish):
    mock_http(monkeypatch,lambda req:httpx.Response(200,json={'choices':[{'finish_reason':finish,'message':{'content':content}}]}))
    with pytest.raises(ValueError): asyncio.run(infer([{'page':1,'text':'test'}],config=config()))

def test_save_redacts_key_and_preserves_it(client):
    from backend.app.services.ai_provider import CONFIG_ENV_PATH
    from dotenv import dotenv_values
    result=client.put('/api/settings/ai',json={'provider':'openrouter','model':'test/model','api_key':FAKE_KEY})
    assert result.status_code==200 and FAKE_KEY not in result.text
    assert result.json()['api_key_configured'] is True
    assert dotenv_values(CONFIG_ENV_PATH)['OPENROUTER_API_KEY']==FAKE_KEY
    result=client.get('/api/settings')
    assert result.json()['ai_provider']=='openrouter' and FAKE_KEY not in result.text
    client.put('/api/settings/ai',json={'provider':'openrouter','model':'test/other'})
    assert snapshot().api_key.get_secret_value()==FAKE_KEY
    client.put('/api/settings/ai',json={'provider':'openrouter','model':'test/other','clear_api_key':True})
    assert not snapshot().api_key.get_secret_value()
    logs=client.get('/api/audit').text
    assert FAKE_KEY not in logs

def test_cloud_upload_requires_document_consent(client,pdf_bytes,extracted,monkeypatch):
    cloud(monkeypatch);seen=[]
    async def fake_infer(chunk,config): seen.append(config);return extracted
    monkeypatch.setattr('backend.app.services.pipeline.infer',fake_infer)
    files={'file':('synthetic-test.pdf',pdf_bytes,'application/pdf')}
    assert client.post('/api/documents',files=files).status_code==403
    assert not seen and client.get('/api/documents').json()==[]
    data={'cloud_consent':'true','expected_provider':'openrouter','expected_model':'test/wrong'}
    assert client.post('/api/documents',files=files,data=data).status_code==409
    data['expected_model']='test/model'
    response=client.post('/api/documents',files=files,data=data)
    assert response.status_code==201,response.text
    assert seen and seen[0].external_authorized and seen[0].model=='test/model'
    with SessionLocal() as db:
        log=db.scalar(select(Audit).where(Audit.action=='external_ai_authorized'))
        assert log.detail['provider']=='openrouter' and log.detail['authorized'] is True
        assert FAKE_KEY not in json.dumps(log.detail)

def test_cloud_retry_requires_new_consent(client,pdf_bytes,extracted,monkeypatch):
    cloud(monkeypatch)
    async def fail(chunk,config): raise ValueError('Synthetic inference failure')
    monkeypatch.setattr('backend.app.services.pipeline.infer',fail)
    data={'cloud_consent':'true','expected_provider':'openrouter','expected_model':'test/model'}
    r=client.post('/api/documents',files={'file':('test.pdf',pdf_bytes,'application/pdf')},data=data)
    doc=r.json()['id']
    assert client.post('/api/documents/'+doc+'/retry').status_code==403
    async def succeed(chunk,config): return extracted
    monkeypatch.setattr('backend.app.services.pipeline.infer',succeed)
    assert client.post('/api/documents/'+doc+'/retry',json={'cloud_consent':True,'expected_provider':'openrouter','expected_model':'test/model'}).status_code==200

def test_connection_check_is_metadata_only(client,monkeypatch):
    cloud(monkeypatch);paths=[]
    def handler(request):
        paths.append((request.method,request.url.path))
        if request.url.path.endswith('/key'): return httpx.Response(200,json={'data':{'limit':1}})
        return httpx.Response(200,json={'data':[{'id':'test/model','supported_parameters':['structured_outputs']},{'id':'test/no-schema','supported_parameters':[]}]})
    mock_http(monkeypatch,handler)
    result=client.post('/api/settings/ai/check')
    assert result.status_code==200 and result.json()['model_available'] is True
    assert result.json()['available_models']==[{'id':'test/model','name':'test/model'}]
    assert paths==[('GET','/api/v1/key'),('GET','/api/v1/models')]

def test_viewer_cannot_change_provider(client):
    client.post('/api/users',json={'email':'viewer-cloud@test.local','name':'Viewer','password':'Viewer-test-password!','role':'viewer'})
    client.post('/api/auth/logout');client.post('/api/auth/login',json={'email':'viewer-cloud@test.local','password':'Viewer-test-password!'})
    assert client.put('/api/settings/ai',json={'provider':'openrouter','model':'test/model','api_key':FAKE_KEY}).status_code==403
    assert client.post('/api/settings/ai/check').status_code==403
