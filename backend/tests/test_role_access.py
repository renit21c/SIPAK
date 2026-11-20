from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import User,Role
from backend.app.security import password_hash


def test_legacy_accounts_consolidated_without_password_change(client):
    password='Synthetic-legacy-password!'
    with SessionLocal() as db:
        for role in ['admin','investigator','reviewer','decision_maker','viewer']:
            db.add(Role(name=role,permissions=[]))
        db.flush()
        for role in ['admin','investigator','reviewer','decision_maker','viewer']:
            db.add(User(name='Synthetic legacy user',email='legacy-'+role+'@test.local',password=password_hash(password),role=role))
        db.commit()
    with TestClient(app) as restarted:
        for role in ['admin','investigator','reviewer','decision_maker','viewer']:
            result=restarted.post('/api/auth/login',json={'email':'legacy-'+role+'@test.local','password':password})
            assert result.status_code==200
            user=result.json();assert user['role']=='komdis'
            assert {'upload','review','analyze'}.issubset(user['permissions'])
            assert 'decide' not in user['permissions']
            restarted.post('/api/auth/logout')


def test_single_role_uses_complete_workspace(client):
    user=client.get('/api/auth/me').json()
    assert user['role']=='komdis'
    assert client.get('/api/users').status_code==200
    assert client.get('/api/audit').status_code==200
    assert client.get('/api/settings').status_code==200
