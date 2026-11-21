import json
from pydantic import SecretStr
import pytest
from sqlalchemy import select
from backend.app.database import SessionLocal
from backend.app.models import Case,Record
from backend.app.schemas import EvaluationDraftText
from backend.app.services import evaluation_draft as service
from backend.app.services.ai_provider import InferenceConfig
from backend.tests.test_sipak import verify
from backend.tests.test_recommendation import evaluation

def draft_text(ids=None,source=None):
    return EvaluationDraftText(summary='BAP halaman 1 mencatat pemeriksaan Budi Uji sebagai saksi.',recommendation='Meminta pendalaman fakta sebelum menentukan tindak lanjut.',basis='Keterangan sumber masih perlu dilengkapi; pasal terpilih adalah referensi pendalaman.',article_ids=ids or [],sources=[source or {'page':1,'quote':'Nomor BAP: TEST-01'}])

def request(case,**changes):
    return {'expected_revision':case['revision'],'expected_assessment_id':case['latest_assessment_id'],**changes}

def test_draft_is_not_approval_and_can_be_supervised(case,client,monkeypatch):
    path='/api/cases/'+case['id'];assert client.post(path+'/evaluation/draft',json=request(case)).status_code==409
    c=verify(client,case)
    async def fake(current,options,config):
        return {**draft_text([options[0]['id']]).model_dump(),'category':'Belum ditentukan','sanction':'Pendalaman fakta.'}
    monkeypatch.setattr('backend.app.main.generate_draft',fake)
    result=client.post(path+'/evaluation/draft',json=request(c));assert result.status_code==200,result.text
    draft=result.json();assert len(draft['articles'])==1
    detail=client.get(path).json();assert detail['ai_draft']['id']==draft['id']
    assert not detail['recommendation_ready'] and client.get(path+'/recommendation').status_code==409
    saved=client.post(path+'/evaluation',json=evaluation(c,article_ids=draft['article_ids'],ai_draft_id=draft['id'],human_reviewed=False));assert saved.status_code==422
    saved=client.post(path+'/evaluation',json=evaluation(c,article_ids=draft['article_ids'],ai_draft_id=draft['id']));assert saved.status_code==200
    payload=saved.json()['evaluation']['payload'];assert payload['articles'][0]['text']==draft['articles'][0]['text']
    assert payload['letterhead']['institution_name']=='INSTITUT PEMERINTAHAN DALAM NEGERI'
    reverified=verify(client,saved.json());assert client.get(path).json()['ai_draft'] is None
    assert client.post(path+'/evaluation',json=evaluation(reverified,ai_draft_id=draft['id'])).status_code==409

def test_draft_rechecks_revision_after_model_returns(case,client,monkeypatch):
    c=verify(client,case);path='/api/cases/'+c['id']
    async def concurrent_change(current,options,config):
        with SessionLocal() as db:
            row=db.get(Case,c['id']);row.revision+=1;db.commit()
        return {**draft_text().model_dump(),'category':'Belum ditentukan','sanction':''}
    monkeypatch.setattr('backend.app.main.generate_draft',concurrent_change)
    assert client.post(path+'/evaluation/draft',json=request(c)).status_code==409
    with SessionLocal() as db:assert not db.scalar(select(Record).where(Record.kind=='ai_evaluation_draft'))

def test_draft_requires_consent_for_current_cloud_model(case,client,monkeypatch):
    from backend.app.config import settings
    c=verify(client,case)
    monkeypatch.setattr(settings,'ai_provider','openrouter');monkeypatch.setattr(settings,'ai_model','test/model');monkeypatch.setattr(settings,'openrouter_api_key',SecretStr('synthetic-test-key'))
    async def never(*args):raise AssertionError('No paid inference allowed in this test.')
    monkeypatch.setattr('backend.app.main.generate_draft',never)
    path='/api/cases/'+c['id']+'/evaluation/draft'
    assert client.post(path,json=request(c)).status_code==403
    assert client.post(path,json=request(c,cloud_consent=True,expected_provider='openrouter',expected_model='old/model')).status_code==409

@pytest.mark.parametrize('bad',['foreign-id','bad-source','empty-source','duplicate'])
def test_ai_cannot_invent_articles_or_sources(case,client,monkeypatch,bad):
    c=verify(client,case);options=client.get('/api/evaluation/articles').json();key=options[0]['id']
    async def fake(*args):
        return draft_text(['invented-id'] if bad=='foreign-id' else [key,key] if bad=='duplicate' else [],{'page':99,'quote':'Kutipan palsu'} if bad=='bad-source' else {'page':1,'quote':'   '} if bad=='empty-source' else None)
    monkeypatch.setattr(service,'infer_openrouter',fake)
    import asyncio
    with pytest.raises(ValueError):asyncio.run(service.generate_draft(c,options,InferenceConfig('openrouter','test/model',SecretStr('synthetic'),external_authorized=True)))

def test_unsupported_category_stays_undetermined(case,client,monkeypatch):
    c=verify(client,case);options=client.get('/api/evaluation/articles').json()
    async def fake(context,*args):return draft_text([context['pasal_tersedia'][0]['id']])
    monkeypatch.setattr(service,'infer_openrouter',fake)
    import asyncio
    result=asyncio.run(service.generate_draft(c,options,InferenceConfig('openrouter','test/model',SecretStr('synthetic'),external_authorized=True)))
    assert result['category']=='Belum ditentukan' and 'Pendalaman' in result['sanction']
    assert client.post('/api/cases/'+c['id']+'/evaluation',json=evaluation(c,article_ids=['invented-id'])).status_code==422

def test_cloud_draft_uses_its_own_strict_schema_without_real_inference(case,client,monkeypatch):
    import asyncio
    import httpx
    from backend.tests.test_cloud_ai import mock_http
    c=verify(client,case);options=client.get('/api/evaluation/articles').json();bodies=[]
    def handler(request):
        body=json.loads(request.content);bodies.append(body)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':draft_text().model_dump_json()}}]})
    mock_http(monkeypatch,handler)
    result=asyncio.run(service.generate_draft(c,options,InferenceConfig('openrouter','nvidia/nemotron-3.5-super-vl',SecretStr('synthetic'),external_authorized=True)))
    assert result['summary'] and len(bodies)==1
    payload=bodies[0];schema=payload['response_format']['json_schema']
    assert 'dari sudut pandang kelembagaan Komisi Disiplin' in payload['messages'][0]['content']
    assert 'Komdis bukan penerima pelimpahan' in payload['messages'][0]['content']
    assert 'telaah Komdis' not in result['sanction']
    assert schema['strict'] and schema['name']=='komdis_evaluation_draft'
    assert 'article_ids' in schema['schema']['required'] and 'sources' in schema['schema']['required']
    assert payload['reasoning']=={'enabled':False} and payload['provider']['zdr']

def test_category_and_sanction_require_complete_selected_match(case,client,monkeypatch):
    import asyncio
    c=verify(client,case);options=client.get('/api/evaluation/articles').json();chosen=options[0]
    async def fake(*args):return draft_text([chosen['id']])
    monkeypatch.setattr(service,'infer_openrouter',fake)
    base={'regulation_id':chosen['regulation_id'],'article':chosen['number'],'category':'Ringan','sanction':'Usulan pembinaan sintetis','missing':[]}
    c['analysis']=[base]
    config=InferenceConfig('openrouter','test/model',SecretStr('synthetic'),external_authorized=True)
    result=asyncio.run(service.generate_draft(c,options,config))
    assert result['category']=='Ringan' and result['sanction']=='Usulan pembinaan sintetis'
    c['analysis']=[{**base,'missing':['praja_level']}]
    result=asyncio.run(service.generate_draft(c,options,config));assert result['category']=='Belum ditentukan'

def test_approved_letterhead_is_frozen_and_invalid_logos_rejected(case,client):
    c=verify(client,case);path='/api/cases/'+c['id'];profile=client.get('/api/settings/letterhead').json()
    result=client.put('/api/settings/letterhead',json={**profile,'logo_right':'data:image/svg+xml;base64,AAAA'});assert result.status_code==422
    profile['unit_name']='KOMDIS SIMULASI';assert client.put('/api/settings/letterhead',json=profile).status_code==200
    assert client.post(path+'/evaluation',json=evaluation(c)).status_code==200
    assert client.put('/api/settings/letterhead',json={**profile,'unit_name':'UNIT BARU'}).status_code==200
    saved=client.get(path).json()['evaluation']['payload'];assert saved['letterhead']['unit_name']=='KOMDIS SIMULASI'
    import fitz
    with fitz.open(stream=client.get(path+'/recommendation').content,filetype='pdf') as pdf:
        text=' '.join(page.get_text() for page in pdf)
        assert 'KOMDIS SIMULASI' in text and 'UNIT BARU' not in text and 'Tanda tangan' not in text
        assert 'Jatinangor' in text and len(pdf[0].get_images())>=1
