import pytest

@pytest.mark.parametrize('role,can_upload,can_review,can_decide',[
    ('admin',True,True,False),
    ('investigator',True,False,False),
    ('reviewer',True,True,False),
    ('decision_maker',False,True,True),
    ('viewer',False,False,False),
])
def test_role_actions_enforced_after_login(client,case,pdf_bytes,role,can_upload,can_review,can_decide):
    email=f'{role}-access@test.local'
    if role!='admin':
        result=client.post('/api/users',json={'email':email,'name':'Synthetic Role Test','password':'Synthetic-role-password!','role':role})
        assert result.status_code==200
        client.post('/api/auth/logout')
        assert client.post('/api/auth/login',json={'email':email,'password':'Synthetic-role-password!'}).status_code==200
    assert client.get('/api/cases').status_code==200
    assert client.get('/api/cases/'+case['id']+'/report').status_code==200
    assert client.get('/api/users').status_code==(200 if role=='admin' else 403)
    assert client.get('/api/audit').status_code==(200 if role=='admin' else 403)
    upload=client.post('/api/documents',files={'file':('synthetic-role-test.pdf',pdf_bytes,'application/pdf')})
    assert upload.status_code==(201 if can_upload else 403)
    review=client.put('/api/cases/'+case['id']+'/review',json={'extraction':case['extraction'],'note':'Synthetic review authorization test.','approve':False,'expected_revision':case['revision']})
    assert review.status_code==(200 if can_review else 403)
    decision=client.post('/api/cases/'+case['id']+'/decisions',json={'number':'SYNTHETIC-ONLY','sanction':'Synthetic test sanction','basis':'Synthetic test basis only','reason':'Synthetic test reason only','official':'Synthetic Officer','date':'2026-11-20'})
    # Permission is necessary but cannot bypass the real examination prerequisites.
    assert decision.status_code==(409 if can_decide else 403)
    if role!='admin':
        assert client.put('/api/settings/ai',json={'provider':'openrouter','model':'synthetic/model'}).status_code==403
