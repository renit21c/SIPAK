from pathlib import Path
from sqlalchemy import select
from backend.app.database import SessionLocal
from backend.app.models import Document,Audit,Record
from backend.app.security import PERMISSIONS
from backend.tests.test_sipak import verify
from backend.tests.test_recommendation import evaluation

def test_case_deletion_hides_documents_and_preserves_restorable_evaluation(case,client,pdf_bytes):
    c=verify(client,case);path='/api/cases/'+c['id']
    assert client.post(path+'/evaluation',json=evaluation(c)).status_code==200
    attachment=client.post(path+'/attachments',files={'file':('annex.pdf',pdf_bytes,'application/pdf')}).json()
    assert client.post(path+'/restore').status_code==409
    result=client.delete(path,params={'expected_revision':c['revision']});assert result.status_code==200,result.text
    assert client.get('/api/cases').json()==[] and client.get('/api/documents').json()==[]
    deleted=client.get('/api/cases?deleted=true').json();assert [item['id'] for item in deleted]==[c['id']]
    for url in [path,path+'/recommendation',path+'/report','/api/documents/'+c['document']['id']+'/pdf','/api/attachments/'+attachment['id']+'/pdf']:
        assert client.get(url).status_code==404,url
    assert client.delete(path,params={'expected_revision':c['revision']}).status_code==404
    with SessionLocal() as db:
        doc=db.get(Document,c['document']['id']);assert doc.deleted and Path(doc.path).exists()
        assert db.scalar(select(Record).where(Record.case_id==c['id'],Record.kind=='evaluation'))
    restored=client.post(path+'/restore');assert restored.status_code==200
    assert restored.json()['recommendation_ready'] and restored.json()['revision']==c['revision']
    assert client.get('/api/cases?deleted=true').json()==[]
    assert client.get(path+'/recommendation').status_code==200
    assert client.get('/api/attachments/'+attachment['id']+'/pdf').status_code==200
    with SessionLocal() as db:
        events=[row.action for row in db.scalars(select(Audit).where(Audit.target==c['id']))]
        assert 'case_deleted' in events and 'case_restored' in events

def test_deletion_rejects_stale_revision_and_missing_permissions(case,client,monkeypatch):
    path='/api/cases/'+case['id']
    assert client.delete(path,params={'expected_revision':case['revision']-1}).status_code==409
    assert client.get(path).status_code==200
    monkeypatch.setitem(PERMISSIONS,'komdis',['read'])
    assert client.delete(path,params={'expected_revision':case['revision']}).status_code==403
    assert client.post(path+'/restore').status_code==403
