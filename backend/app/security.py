import hashlib, hmac, secrets
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from .database import get_db
from .models import User, Session, Role, Audit

PERMISSIONS = {
    'komdis': ['read','upload','review','analyze','regulations','users','delete'],
}

def password_hash(password):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384,r=8,p=1).hex()

def password_matches(password, encoded):
    salt, value = encoded.split(':')
    return hmac.compare_digest(hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex(), value)

def audit(db, user, action, target, detail=None):
    db.add(Audit(user_id=user.id if user else None, action=action, target=target, detail=detail or {}))

def current_user(request: Request, db: DBSession = Depends(get_db)):
    token = request.cookies.get('sipak_session', '')
    session = db.get(Session, hashlib.sha256(token.encode()).hexdigest())
    if not session or session.expires < datetime.now(timezone.utc).isoformat():
        raise HTTPException(401, 'Sesi berakhir. Silakan masuk kembali.')
    user = db.get(User, session.user_id)
    if not user or not user.active: raise HTTPException(401, 'Akun tidak aktif.')
    return user

def require(permission):
    def check(user: User = Depends(current_user)):
        if permission not in PERMISSIONS.get(user.role, []):
            raise HTTPException(403, 'Peran Anda tidak memiliki kewenangan untuk tindakan ini.')
        return user
    return check

def public_user(user):
    return {'id':user.id,'name':user.name,'email':user.email,'role':user.role,'permissions':PERMISSIONS[user.role]}
