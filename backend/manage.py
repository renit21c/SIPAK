"""Local administrator setup; passwords are entered without echo."""
import argparse
from getpass import getpass
from sqlalchemy import select
from .app.database import Base, engine, SessionLocal
from .app.models import User, Role
from .app.security import PERMISSIONS, password_hash, audit

def main():
    parser=argparse.ArgumentParser(description='Administrasi lokal SIPAK')
    parser.add_argument('command',choices=['init','reset-password','seed-regulations'])
    parser.add_argument('--email',default='admin@sipak.local')
    parser.add_argument('--name',default='Administrator SIPAK')
    args=parser.parse_args()
    if args.command=='seed-regulations':
        from .app.services.builtin_regulation import seed_builtin_regulation, bundled_data
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            installed=seed_builtin_regulation(db)
            db.commit()
        manifest,articles,rules=bundled_data()
        print(f"Regulasi {'dipasang' if installed else 'sudah tersedia'}: {len(articles)} pasal, {len(rules)} aturan; SHA-256 {manifest['sha256']}")
        return
    password=getpass('Kata sandi (minimal 12 karakter): ')
    if len(password)<12: raise SystemExit('Kata sandi minimal 12 karakter.')
    if password!=getpass('Ulangi kata sandi: '): raise SystemExit('Kata sandi tidak sama.')
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for role,permissions in PERMISSIONS.items():
            if not db.get(Role,role): db.add(Role(name=role,permissions=permissions))
        db.flush()
        user=db.scalar(select(User).where(User.email==args.email.lower()))
        if args.command=='init':
            if db.scalar(select(User)): raise SystemExit('Pengguna sudah tersedia. Buat pengguna berikutnya melalui Pengaturan.')
            user=User(email=args.email.lower(),name=args.name,password=password_hash(password),role='komdis')
            db.add(user); db.flush(); audit(db,user,'administrator_initialized',user.id)
        else:
            if not user: raise SystemExit('Pengguna tidak ditemukan.')
            user.password=password_hash(password)
            from .app.models import Session
            from sqlalchemy import delete
            db.execute(delete(Session).where(Session.user_id==user.id))
            audit(db,user,'password_reset_locally',user.id)
        db.commit()
    print('Akun tersimpan. Masuk menggunakan email yang dipilih.')

if __name__=='__main__': main()
