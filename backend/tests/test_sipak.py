import json
import pytest
import fitz
from backend.app.schemas import Extraction
from backend.app.services.documents import chunks, extract_pages
from backend.app.services.extraction import validate_sources, aggregate
from backend.app.database import SessionLocal
from backend.app.models import DocumentPage, Assessment, Regulation, Article, Provision, User, Role
from backend.app.security import password_hash

def test_anonymous_and_csrf(client):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as anon:
        assert anon.get('/api/documents').status_code==401
        assert anon.get('/api/cases').status_code==401
    r=client.post('/api/auth/logout',headers={'origin':'https://untrusted.example'})
    assert r.status_code==403
    assert client.get('/api/auth/me').status_code==200

def test_upload_validation(client,pdf_bytes):
    assert client.post('/api/documents',files={'file':('evil.pdf',b'not a pdf','application/pdf')}).status_code==400
    assert client.post('/api/documents',files={'file':('bad.txt',pdf_bytes,'text/plain')}).status_code==400

def test_pdf_extraction_and_citations(case,client):
    assert case['information']['bap_number']=='TEST-01'
    assert case['persons'][0]['role']=='Saksi'
    assert not case['verified']
    assert case['analysis']==[]
    assert case['document']['status']=='Berhasil'
    doc=client.get('/api/documents/'+case['document']['id']+'/pdf')
    assert doc.status_code==200 and doc.content.startswith(b'%PDF-')
    assert client.delete('/api/documents/'+case['document']['id']).status_code==409
    with SessionLocal() as db:
        from sqlalchemy import select
        pages=db.scalars(select(DocumentPage)).all()
        assert len(pages)==1 and 'Budi Uji' in pages[0].text

def test_source_hallucinations_are_withheld(extracted):
    data=extracted.model_dump(); data['involved_persons'][0]['sources'][0]['quote']='Kutipan karangan'
    checked=validate_sources(Extraction.model_validate(data),[{'page':1,'text':'Nomor BAP: TEST-01'}])
    assert checked.involved_persons==[]
    assert checked.missing_information
    data=Extraction.model_validate({'evidence':[{'name':'barang khayalan'}]})
    assert validate_sources(data,[{'page':1,'text':'Sumber'}]).evidence==[]

def test_chunking_keeps_pages_and_conflicts(extracted):
    pages=[{'page':8,'text':'a'*22000},{'page':9,'text':'b'*5000}]
    batches=list(chunks(pages));assert len(batches)>=3
    assert {c['page'] for b in batches for c in b}=={8,9}
    second=extracted.model_copy(deep=True);second.case_information.bap_number='CONFLICT'
    result=aggregate([extracted,second])
    assert result.case_information.bap_number=='TEST-01'
    assert any('Perbedaan' in m for m in result.missing_information)
    assert len(result.involved_persons)==1

def test_inference_failure_is_not_success(client,pdf_bytes,monkeypatch):
    async def fail(chunk,**kwargs): raise ValueError('Ollama belum terhubung (pengujian).')
    monkeypatch.setattr('backend.app.services.pipeline.infer',fail)
    response=client.post('/api/documents',files={'file':('test.pdf',pdf_bytes,'application/pdf')})
    assert response.status_code==201
    doc=client.get('/api/documents').json()[0]
    assert doc['status']=='Gagal' and 'Ollama' in doc['error']
    assert client.get('/api/cases').json()==[]
    assert client.delete('/api/documents/'+doc['id']).status_code==200
    assert client.get('/api/documents/'+doc['id']+'/pdf').status_code==404

def test_scanned_pdf_rejected(client,monkeypatch):
    doc=fitz.open();doc.new_page();binary=doc.tobytes();doc.close()
    response=client.post('/api/documents',files={'file':('scan.pdf',binary,'application/pdf')})
    assert response.status_code==201
    data=client.get('/api/documents').json()[0]
    assert data['status']=='Gagal' and 'OCR' in data['error']

def verify(client,case):
    r=client.put('/api/cases/'+case['id']+'/review',json={'extraction':case['extraction'],'note':'Sumber diperiksa dalam pengujian.','approve':True,'expected_revision':case['revision']})
    assert r.status_code==200,r.text
    return r.json()

def test_review_validation_and_revision(case,client):
    before=case['revision']
    bad=json.loads(json.dumps(case['extraction']));bad['case_information']['sources'][0]['page']=999
    assert client.put('/api/cases/'+case['id']+'/review',json={'extraction':bad,'note':'Periksa kutipan.','approve':True,'expected_revision':before}).status_code==422
    reviewed=verify(client,case)
    assert reviewed['verified'] and reviewed['revision']==before+1
    assert reviewed['records'][-1]['payload']['extraction_snapshot']
    assert client.put('/api/cases/'+case['id']+'/review',json={'extraction':case['extraction'],'note':'Revisi lama ditolak.','approve':True,'expected_revision':before}).status_code==409

def test_komdis_and_logout(client,case):
    r=client.post('/api/users',json={'email':'komdis@test.local','name':'Anggota Pengujian','password':'Komdis-password-test!'})
    assert r.status_code==200 and r.json()['role']=='komdis'
    assert client.post('/api/users',json={'email':'old@test.local','name':'Old Role','password':'Something-long-test!','role':'viewer'}).status_code==422
    client.post('/api/auth/logout')
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':'komdis@test.local','password':'Komdis-password-test!'}).status_code==200
    assert client.get('/api/cases').status_code==200
    assert client.post('/api/cases/'+case['id']+'/notes',json={'text':'Catatan evaluasi anggota Komdis.'}).status_code==200
    assert client.post('/api/cases/'+case['id']+'/decisions',json={'number':'SK-UJI','sanction':'Sanksi sintetis','basis':'Dasar pengujian sintetis','reason':'Alasan pengujian sintetis','official':'Pejabat Uji','date':'2026-01-01'}).status_code==403


def regulation_pdf():
    doc=fitz.open();p=doc.new_page()
    p.insert_text((40,50),'REGULASI SINTETIS PENGUJIAN - BUKAN REGULASI BERLAKU\nPasal 1\n(1) Ketentuan uji perilaku dan tingkat dengan syarat tertentu.\nPasal 2\n(1) Sanksi uji hanya untuk data pengujian.')
    data=doc.tobytes();doc.close();return data

def import_reg(client,version='test-v1'):
    r=client.post('/api/regulations',data={'title':'Regulasi Sintetis Pengujian','number':'UJI-ONLY','version':version,'effective_date':'2026-01-01','source_url':'https://example.invalid/test'},files={'file':('reg-pengujian.pdf',regulation_pdf(),'application/pdf')})
    assert r.status_code==200,r.text
    return next(r for r in client.get('/api/regulations').json() if r['version']==version)

def test_regulation_versioning_and_matching(case,client):
    c=verify(client,case);reg=import_reg(client);reg2=import_reg(client,'test-v2')
    assert reg['id']!=reg2['id'] and len([r for r in client.get('/api/regulations').json() if not r.get('builtin')])==2
    a=reg['articles'];assert [x['number'] for x in a]==[1,2]
    rule={'article_id':a[0]['id'],'paragraph':'1','letter':'','text':'Ketentuan uji perilaku dan tingkat dengan syarat tertentu.','category':'Ringan','sanction':'Sanksi uji','sanction_basis':'Sanksi uji hanya untuk data pengujian.','sanction_article_id':a[1]['id'],'conditions':[{'field':'conduct','equals':'uji'},{'field':'praja_level','equals':'Pratama'},{'field':'repetition','equals':False}]}
    assert client.post('/api/rules',json=rule).status_code==409
    assert client.post('/api/regulations/'+reg['id']+'/verify').status_code==200
    bad=rule|{'text':'Bunyi pasal karangan yang tidak ada'}
    assert client.post('/api/rules',json=bad).status_code==422
    assert client.post('/api/rules',json=rule).status_code==200
    source=[{'page':1,'quote':'Nomor BAP: TEST-01'}]
    facts={'conduct':{'value':'uji','sources':source},'praja_level':{'value':'Pratama','sources':source}}
    path='/api/cases/'+c['id']+'/analysis'
    r=client.post(path,json={'facts':facts,'note':'Penilaian data pengujian.'});assert r.status_code==200,r.text
    assert r.json()['matches'][0]['category'] is None
    assert r.json()['matches'][0]['missing']==['repetition']
    facts['repetition']={'value':False,'sources':source}
    r=client.post(path,json={'facts':facts,'note':'Seluruh kondisi data uji.'})
    assert r.json()['matches'][0]['category']=='Ringan'
    assert r.json()['matches'][0]['version']=='test-v1'
    facts['praja_level']['value']='Madya'
    assert client.post(path,json={'facts':facts,'note':'Tingkat berbeda, harus tidak cocok.'}).json()['matches']==[]
    facts['conduct']['sources']=[{'page':1,'quote':'Sumber palsu'}]
    assert client.post(path,json={'facts':facts,'note':'Sumber palsu ditolak.'}).status_code==422

def test_legacy_decision_archive_stays_locked(case,client):
    from backend.app.models import Decision,Case
    c=verify(client,case);path='/api/cases/'+c['id']
    with SessionLocal() as db:
        user=db.query(User).first()
        db.add(Decision(case_id=c['id'],created_by=user.id,number='SK-UJI-01',sanction='Keputusan sintetis uji',basis='Ketentuan pengujian saja',reason='Pertimbangan pengujian saja',official='Pejabat Pengujian',date='2026-01-01'))
        db.get(Case,c['id']).status='Keputusan Resmi Diterbitkan';db.commit()
    assert client.post(path+'/notes',json={'text':'Perkara telah dikunci.'}).status_code==409
    report=client.get(path+'/report');assert report.status_code==200
    with fitz.open(stream=report.content,filetype='pdf') as pdf:
        body=' '.join(p.get_text() for p in pdf)
        assert 'BUKAN DOKUMEN KEPUTUSAN RESMI' in body
        assert 'SK-UJI-01' in body and 'Budi Uji' in body


def test_login_rate_limit(client):
    for _ in range(8):
        assert client.post('/api/auth/login',json={'email':'wrong@test.local','password':'no'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'wrong@test.local','password':'no'}).status_code==429
