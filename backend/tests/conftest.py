import os
import tempfile
from pathlib import Path

TEST_ROOT=Path(tempfile.mkdtemp(prefix='sipak-tests-'))
os.environ['DATABASE_URL']='sqlite:///'+str(TEST_ROOT/'tests.db')
os.environ['STORAGE_PATH']=str(TEST_ROOT/'documents')
os.environ['BOOTSTRAP_EMAIL']='admin@test.local'
os.environ['BOOTSTRAP_PASSWORD']='Test-only-password-2026!'
os.environ['AI_PROVIDER']='ollama'
os.environ['AI_MODEL']=''
os.environ['OPENROUTER_API_KEY']=''

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, attempts
from backend.app.database import Base, engine

@pytest.fixture(autouse=True)
def isolated_ai_configuration(monkeypatch,tmp_path):
    from pydantic import SecretStr
    from backend.app.config import settings
    import backend.app.services.ai_provider as provider
    monkeypatch.setattr(provider,'CONFIG_ENV_PATH',tmp_path/'.env')
    for field,value in {'ai_provider':'ollama','ai_model':'','openrouter_api_key':SecretStr(''),'ollama_model':'qwen2.5:3b-instruct-q4_K_M'}.items():
        monkeypatch.setattr(settings,field,value)
    for name,value in {'AI_PROVIDER':'ollama','AI_MODEL':'','OPENROUTER_API_KEY':'','OLLAMA_MODEL':'qwen2.5:3b-instruct-q4_K_M'}.items():
        monkeypatch.setenv(name,value)

@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    attempts.clear()
    with TestClient(app) as c:
        response=c.post('/api/auth/login',json={'email':'admin@test.local','password':'Test-only-password-2026!'})
        assert response.status_code==200
        yield c

@pytest.fixture
def pdf_bytes():
    import fitz
    doc=fitz.open(); page=doc.new_page()
    page.insert_text((40,50),'DOKUMEN SINTETIS PENGUJIAN - BUKAN PERKARA NYATA\nNomor BAP: TEST-01\nNama: Budi Uji\nTingkat: Pratama\nBudi diperiksa sebagai Saksi.\nKejadian dilaporkan pada 1 Januari 2026.')
    data=doc.tobytes();doc.close();return data

@pytest.fixture
def extracted():
    from backend.app.schemas import Extraction
    return Extraction.model_validate({'case_information':{'bap_number':'TEST-01','sources':[{'page':1,'quote':'Nomor BAP: TEST-01'}]},'involved_persons':[{'name':'Budi Uji','praja_level':'Pratama','role':'Saksi','sources':[{'page':1,'quote':'Nama: Budi Uji\nTingkat: Pratama\nBudi diperiksa sebagai Saksi.'}]}]})

@pytest.fixture
def case(client,pdf_bytes,extracted,monkeypatch):
    async def fake_infer(chunk,**kwargs): return extracted
    monkeypatch.setattr('backend.app.services.pipeline.infer',fake_infer)
    response=client.post('/api/documents',files={'file':('pengujian.pdf',pdf_bytes,'application/pdf')})
    assert response.status_code==201,response.text
    cases=client.get('/api/cases').json();assert len(cases)==1
    return client.get('/api/cases/'+cases[0]['id']).json()
