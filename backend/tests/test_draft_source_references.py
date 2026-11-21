import asyncio
import copy
import json

import httpx
from pydantic import SecretStr
import pytest

from backend.app.schemas import Extraction
from backend.app.services import evaluation_draft as service
from backend.app.services.ai_provider import InferenceConfig,strict_schema
from backend.tests.test_evaluation_draft import model_draft
from backend.tests.test_sipak import verify

def config():return InferenceConfig('openrouter','synthetic/model',SecretStr('synthetic-only'),external_authorized=True)

@pytest.mark.parametrize('quote',[
    'Nama:\u00a0Budi Uji\nPeran: Saksi',
    'Keterangan diperiksa\n  pada pukul 20.18 WIB.',
    'Saksi menyebut “20.00–20.18” dalam keterangannya.',
    'Nomor BAP: UJI-\u200b001; kata berligatur ﬁ dan soft\u00adhyphen.',
])
def test_ocr_typography_is_returned_verbatim_without_model_copying_it(monkeypatch,quote):
    extraction=Extraction().model_dump()
    extraction['case_information']['sources']=[{'page':7,'quote':quote}]
    original=copy.deepcopy(extraction)
    async def infer(context,system,config,output_model,*args):
        assert context['bap_terverifikasi']['case_information']['source_ids']==['S001']
        assert 'sources' not in context['bap_terverifikasi']['case_information']
        assert 'Jangan menulis ulang kutipan' in system
        return output_model.model_validate(model_draft().model_dump())
    monkeypatch.setattr(service,'infer_openrouter',infer)
    result=asyncio.run(service.generate_draft({'extraction':extraction,'analysis':[]},[],config()))
    assert result['sources']==[{'page':7,'quote':quote}]
    assert 'source_ids' not in result and extraction==original

def test_catalog_deduplicates_same_page_sources_without_merging_other_pages():
    extraction=Extraction().model_dump()
    extraction['case_information']['sources']=[{'page':2,'quote':'Nomor BAP: UJI-01'}]
    extraction['involved_persons']=[{'name':'Uji','sources':[{'page':2,'quote':'Nomor  BAP: UJI-01'},{'page':3,'quote':'Nomor BAP: UJI-01'}]}]
    facts,catalog=service.verified_source_catalog(extraction)
    assert catalog==[{'id':'S001','page':2,'quote':'Nomor BAP: UJI-01'},{'id':'S002','page':3,'quote':'Nomor BAP: UJI-01'}]
    assert facts['involved_persons'][0]['source_ids']==['S001','S002']
    schema=strict_schema(service.reference_schema(catalog))
    assert schema['$defs']['VerifiedSourceId']['enum']==['S001','S002']
    assert 'sources' not in schema['properties']

def test_missing_verified_quotes_stop_before_paid_inference(monkeypatch):
    async def forbidden(*args):pytest.fail('No usable verified source; do not call the model')
    monkeypatch.setattr(service,'infer_openrouter',forbidden)
    extraction=Extraction().model_dump()
    extraction['case_information']['sources']=[{'page':1,'quote':' \n '}]
    with pytest.raises(ValueError,match='belum memiliki kutipan'):
        asyncio.run(service.generate_draft({'extraction':extraction,'analysis':[]},[],config()))

def test_repeated_reference_ids_return_one_canonical_quote(case,client,monkeypatch):
    current=verify(client,case)
    async def infer(*args):return model_draft(source_ids=['S001','S001'])
    monkeypatch.setattr(service,'infer_openrouter',infer)
    result=asyncio.run(service.generate_draft(current,[],config()))
    assert result['sources']==[{'page':1,'quote':'Nomor BAP: TEST-01'}]

def test_endpoint_keeps_public_source_shape_and_requires_human_approval(case,client,monkeypatch):
    current=verify(client,case)
    from backend.app.config import settings
    monkeypatch.setattr(settings,'ai_provider','openrouter');monkeypatch.setattr(settings,'ai_model','synthetic/model');monkeypatch.setattr(settings,'openrouter_api_key',SecretStr('synthetic-only'))
    async def infer(context,*args):return model_draft(source_ids=[context['sumber_terverifikasi'][-1]['id']])
    monkeypatch.setattr(service,'infer_openrouter',infer)
    response=client.post('/api/cases/'+current['id']+'/evaluation/draft',json={'expected_revision':current['revision'],'expected_assessment_id':current['latest_assessment_id'],'cloud_consent':True,'expected_provider':'openrouter','expected_model':'synthetic/model'})
    assert response.status_code==200,response.text
    draft=response.json()
    assert draft['sources']==current['persons'][0]['sources'] and 'source_ids' not in draft
    saved=client.get('/api/cases/'+current['id']).json()
    assert saved['ai_draft']['sources']==draft['sources'] and not saved['recommendation_ready']

def test_local_model_also_selects_closed_source_ids(case,client,monkeypatch):
    current=verify(client,case);captured=[]
    real_client=httpx.AsyncClient
    def handler(request):
        body=json.loads(request.content);captured.append(body)
        assert body['format']['$defs']['VerifiedSourceId']['enum']==['S001','S002']
        return httpx.Response(200,json={'done':True,'done_reason':'stop','message':{'content':model_draft().model_dump_json()}})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    result=asyncio.run(service.generate_draft(current,[],InferenceConfig('ollama','synthetic/model',SecretStr(''))))
    assert len(captured)==1 and result['sources']==[{'page':1,'quote':'Nomor BAP: TEST-01'}]
