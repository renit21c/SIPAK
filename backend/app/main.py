import hashlib, secrets, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DBSession
from .config import settings
from .database import Base, engine, SessionLocal, get_db, now
from .models import *
from .schemas import *
from .security import current_user, require, public_user, password_hash, password_matches, audit, PERMISSIONS
from .services.documents import store_pdf, extract_pages, normalize
from .services.extraction import validate_sources, local_ollama_url
from .services.pipeline import process_document
from .services.cases import document_dict, case_dict, save_extraction
from .services.regulations import split_articles, classify
from .services.reports import generate_report, generate_recommendation
from .services.builtin_regulation import seed_builtin_regulation, builtin_metadata, BUILTIN_ID
from .services.ai_provider import snapshot,public_config,save_configuration,ensure_ready,check_openrouter,OPENROUTER_URL
from .services.letterhead import read_letterhead,save_letterhead
from .services.evaluation_draft import article_options,resolve_articles,generate_draft
import httpx

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for name,permissions in PERMISSIONS.items():
            if not db.get(Role,name): db.add(Role(name=name,permissions=permissions))
        db.flush()
        # Consolidate existing accounts without changing credentials or case history.
        for account in db.scalars(select(User).where(User.role!='komdis')):
            old_role=account.role
            account.role='komdis'
            audit(db,account,'workspace_consolidated',account.id,{'previous_role':old_role,'role':'komdis'})
        seed_builtin_regulation(db)
        if not db.scalar(select(User)) and settings.bootstrap_email and len(settings.bootstrap_password)>=12:
            db.add(User(email=settings.bootstrap_email.lower(),name=settings.bootstrap_name,password=password_hash(settings.bootstrap_password),role='komdis'))
        db.execute(update(Document).where(Document.status.in_(['Menunggu','Sedang Diproses'])).values(status='Gagal',error='Pemrosesan terhenti saat server dimulai ulang. Silakan coba kembali.'))
        db.commit()
    yield

app=FastAPI(title='SIPAK API',version='0.1.0',lifespan=lifespan)
attempts=defaultdict(deque)

@app.middleware('http')
async def protection(request: Request, call_next):
    # Browser writes must be same-origin, including login (CSRF protection).
    origin=request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin:
        from urllib.parse import urlparse
        if urlparse(origin).netloc != request.headers.get('host'):
            return Response('Cross-origin request rejected',403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['X-Frame-Options']='SAMEORIGIN'
    if request.url.path.startswith('/api'): response.headers['Cache-Control']='no-store'
    return response

def get_case(db, case_id):
    case=db.get(Case,case_id)
    if not case or db.get(Document,case.document_id).deleted: raise HTTPException(404,'Perkara tidak ditemukan.')
    return case

def get_document(db, document_id):
    doc=db.get(Document,document_id)
    if not doc or doc.deleted: raise HTTPException(404,'Dokumen tidak ditemukan.')
    return doc

def ensure_mutable(db,case):
    if db.scalar(select(Decision).where(Decision.case_id==case.id)):
        raise HTTPException(409,'Perkara dengan keputusan resmi dikunci untuk menjaga jejak keputusan.')

@app.get('/api/health')
def health(): return {'status':'ok'}

@app.post('/api/auth/login')
def login(data:Login, request:Request, response:Response, db:DBSession=Depends(get_db)):
    key=request.client.host if request.client else 'local'; queue=attempts[key]
    while queue and time.monotonic()-queue[0]>900: queue.popleft()
    if len(queue)>=8: raise HTTPException(429,'Terlalu banyak percobaan. Coba kembali dalam 15 menit.')
    queue.append(time.monotonic())
    user=db.scalar(select(User).where(User.email==data.email.lower()))
    if not user or not user.active or not password_matches(data.password,user.password):
        audit(db,None,'login_failed','auth'); db.commit()
        raise HTTPException(401,'Email atau kata sandi tidak sesuai.')
    queue.clear(); token=secrets.token_urlsafe(48)
    db.add(Session(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=user.id,expires=(datetime.now(timezone.utc)+timedelta(hours=settings.session_hours)).isoformat()))
    audit(db,user,'login',user.id); db.commit()
    response.set_cookie('sipak_session',token,httponly=True,secure=settings.cookie_secure,samesite='strict',max_age=settings.session_hours*3600,path='/')
    return public_user(user)

@app.get('/api/auth/me')
def me(user:User=Depends(current_user)): return public_user(user)

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,user:User=Depends(current_user),db:DBSession=Depends(get_db)):
    token=request.cookies.get('sipak_session','')
    session=db.get(Session,hashlib.sha256(token.encode()).hexdigest())
    if session: db.delete(session)
    audit(db,user,'logout',user.id); db.commit(); response.delete_cookie('sipak_session',path='/')
    return {'ok':True}

@app.get('/api/users')
def users(user:User=Depends(require('users')),db:DBSession=Depends(get_db)):
    return [public_user(u) for u in db.scalars(select(User))]

@app.post('/api/users')
def create_user(data:UserCreate,user:User=Depends(require('users')),db:DBSession=Depends(get_db)):
    if len(data.password)<12: raise HTTPException(400,'Kata sandi minimal 12 karakter.')
    if db.scalar(select(User).where(User.email==data.email.lower())): raise HTTPException(409,'Email telah digunakan.')
    created=User(email=data.email.lower(),name=data.name,role=data.role,password=password_hash(data.password)); db.add(created); db.flush()
    audit(db,user,'user_created',created.id,{'role':data.role}); db.commit(); return public_user(created)

@app.get('/api/settings')
async def system_settings(user:User=Depends(current_user)):
    connected=False; models=[]
    config=public_config()
    if not config['ai_external']:
        try:
            async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
                r=await client.get(local_ollama_url()+'/api/tags'); r.raise_for_status()
                models=[m['name'] for m in r.json().get('models',[])]; connected=True
        except Exception: pass
    return {**config,'ollama_url':settings.ollama_url,'ollama_connected':connected,'ai_connected':connected,'available_models':models,'model_available':config['model'] in models,'max_upload_mb':settings.max_upload_mb,'database':'PostgreSQL' if settings.database_url.startswith('postgresql') else 'SQLite (pengembangan lokal)','bootstrap_required':not bool(settings.bootstrap_email),'workflow':WORKFLOW,'regulatory_source':'https://peraturan.go.id/id/permendagri-no-8-tahun-2026'}

@app.put('/api/settings/ai')
def update_ai(data:AIConfigUpdate,user:User=Depends(require('users')),db:DBSession=Depends(get_db)):
    try: result=save_configuration(data.provider,data.model,data.api_key,data.clear_api_key)
    except ValueError as exc: raise HTTPException(400,str(exc))
    audit(db,user,'ai_configuration_updated','settings',{'provider':data.provider,'model':data.model,'key_changed':bool(data.api_key) or data.clear_api_key})
    db.commit();return result

@app.post('/api/settings/ai/check')
async def check_ai(user:User=Depends(require('users'))):
    if snapshot().external:
        try: return await check_openrouter()
        except ValueError as exc: raise HTTPException(400,str(exc))
    return await system_settings(user)

@app.get('/api/settings/letterhead')
def letterhead(user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    return read_letterhead(db)

@app.put('/api/settings/letterhead')
def update_letterhead(data:Letterhead,user:User=Depends(require('users')),db:DBSession=Depends(get_db)):
    try: result=save_letterhead(db,data)
    except ValueError as exc: raise HTTPException(422,str(exc))
    audit(db,user,'letterhead_updated','settings');db.commit();return result

@app.get('/api/evaluation/articles')
def evaluation_articles(user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    return article_options(db)

def authorized_inference(data:InferenceConsent):
    config=snapshot(authorized=data.cloud_consent)
    if config.external and not data.cloud_consent:
        raise HTTPException(403,'Isi BAP belum diizinkan untuk dikirim ke OpenRouter. Berikan persetujuan untuk dokumen ini.')
    if (config.external and (data.expected_provider!=config.provider or data.expected_model!=config.model)) or (data.expected_provider and data.expected_provider!=config.provider) or (data.expected_model and data.expected_model!=config.model):
        raise HTTPException(409,'Konfigurasi AI berubah. Muat ulang pengaturan dan konfirmasi provider/model yang baru.')
    try: ensure_ready(config)
    except ValueError as exc: raise HTTPException(409,str(exc))
    return config

def audit_inference_consent(db,user,document_id,config):
    audit(db,user,'external_ai_authorized' if config.external else 'local_ai_selected',document_id,{'provider':config.provider,'model':config.model,'destination':OPENROUTER_URL if config.external else settings.ollama_url,'data_scope':'Teks BAP per halaman; identitas, keterangan, bukti dan kronologi','authorized':config.external_authorized})

@app.get('/api/documents')
def documents(user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    cases={c.document_id:c for c in db.scalars(select(Case))}
    return [dict(document_dict(d),case_id=cases[d.id].id if d.id in cases else None,verified=cases[d.id].verified if d.id in cases else False,uploader=db.get(User,d.uploaded_by).name) for d in db.scalars(select(Document).where(Document.deleted==False).order_by(Document.created_at.desc()))]

@app.post('/api/documents',status_code=201)
async def upload(background:BackgroundTasks,file:UploadFile=File(...),cloud_consent:bool=Form(False),expected_provider:str=Form(''),expected_model:str=Form(''),user:User=Depends(require('upload')),db:DBSession=Depends(get_db)):
    config=authorized_inference(InferenceConsent(cloud_consent=cloud_consent,expected_provider=expected_provider,expected_model=expected_model))
    document_id=uid(); path=settings.storage_path/f'{document_id}.pdf'
    size,pages=await store_pdf(file,path)
    doc=Document(id=document_id,name=Path(file.filename.replace('\\','/')).name[:255],path=str(path),size=size,page_count=pages,uploaded_by=user.id)
    db.add(doc); audit(db,user,'document_uploaded',document_id,{'name':doc.name,'size':size})
    audit_inference_consent(db,user,document_id,config);db.commit()
    background.add_task(process_document,document_id,config)
    return document_dict(doc)

@app.post('/api/documents/{document_id}/retry')
def retry(document_id:str,background:BackgroundTasks,data:InferenceConsent=InferenceConsent(),user:User=Depends(require('upload')),db:DBSession=Depends(get_db)):
    doc=get_document(db,document_id)
    if doc.status!='Gagal': raise HTTPException(409,'Hanya dokumen gagal yang dapat diproses ulang.')
    config=authorized_inference(data)
    doc.status='Menunggu'; doc.stage=1; doc.error=None
    audit(db,user,'extraction_retried',doc.id);audit_inference_consent(db,user,doc.id,config)
    db.commit(); background.add_task(process_document,doc.id,config)
    return document_dict(doc)

@app.get('/api/documents/{document_id}/pdf')
def pdf(document_id:str,user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    doc=get_document(db,document_id); audit(db,user,'document_viewed',doc.id); db.commit()
    return FileResponse(doc.path,media_type='application/pdf',filename=doc.name,content_disposition_type='inline')

@app.delete('/api/documents/{document_id}')
def delete_document(document_id:str,user:User=Depends(require('delete')),db:DBSession=Depends(get_db)):
    doc=get_document(db,document_id)
    if doc.status in ('Menunggu','Sedang Diproses'): raise HTTPException(409,'Dokumen masih diproses.')
    if db.scalar(select(Case).where(Case.document_id==doc.id)):
        raise HTTPException(409,'Dokumen terkait perkara tidak dapat dihapus. Gunakan kebijakan retensi institusi.')
    doc.deleted=True; audit(db,user,'document_deleted',doc.id); db.commit()
    Path(doc.path).unlink(missing_ok=True)
    return {'ok':True}

@app.get('/api/cases')
def cases(deleted:bool=False,user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    return [case_dict(db,c) for c in db.scalars(select(Case).order_by(Case.created_at.desc())) if db.get(Document,c.document_id).deleted==deleted]

@app.delete('/api/cases/{case_id}')
def delete_case(case_id:str,expected_revision:int,user:User=Depends(require('delete')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id)
    if case.revision!=expected_revision: raise HTTPException(409,'Perkara berubah. Muat ulang sebelum menghapus.')
    doc=db.get(Document,case.document_id)
    if doc.status in ('Menunggu','Sedang Diproses'): raise HTTPException(409,'BAP masih diproses.')
    doc.deleted=True
    audit(db,user,'case_deleted',case.id,{'revision':case.revision,'recoverable':True});db.commit()
    return {'ok':True}

@app.post('/api/cases/{case_id}/restore')
def restore_case(case_id:str,user:User=Depends(require('delete')),db:DBSession=Depends(get_db)):
    case=db.get(Case,case_id)
    if not case: raise HTTPException(404,'Perkara tidak ditemukan.')
    doc=db.get(Document,case.document_id)
    if not doc.deleted: raise HTTPException(409,'Perkara masih aktif.')
    doc.deleted=False
    audit(db,user,'case_restored',case.id);db.commit()
    return case_dict(db,case)

@app.get('/api/cases/{case_id}')
def detail(case_id:str,user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); audit(db,user,'case_viewed',case.id); db.commit(); return case_dict(db,case,True)

@app.put('/api/cases/{case_id}/review')
def review(case_id:str,data:Review,user:User=Depends(require('review')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); ensure_mutable(db,case)
    if case.revision!=data.expected_revision: raise HTTPException(409,'Data telah diubah pemeriksa lain. Muat ulang sebelum menyimpan.')
    pages=[{'page':p.number,'text':p.text} for p in db.scalars(select(DocumentPage).where(DocumentPage.document_id==case.document_id))]
    validated=validate_sources(data.extraction,pages)
    if validated.model_dump()!=data.extraction.model_dump():
        raise HTTPException(422,'Setiap informasi wajib memiliki kutipan yang cocok dengan halaman sumber. Periksa kembali hasil koreksi.')
    save_extraction(db,case,data.extraction); case.verified=data.approve; case.revision+=1
    case.status='Siap Evaluasi' if data.approve else 'Perlu Perbaikan'
    db.add(Record(case_id=case.id,created_by=user.id,kind='verification',payload={'approved':data.approve,'note':data.note,'revision':case.revision,'extraction_snapshot':data.extraction.model_dump()}))
    audit(db,user,'extraction_reviewed',case.id,{'approved':data.approve,'revision':case.revision}); db.commit()
    return case_dict(db,case,True)

@app.post('/api/cases/{case_id}/analysis')
def analysis(case_id:str,data:AnalysisInput,user:User=Depends(require('analyze')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); ensure_mutable(db,case)
    if not case.verified: raise HTTPException(409,'Verifikasi hasil ekstraksi sebelum melakukan penilaian ketentuan.')
    pages={p.number:normalize(p.text) for p in db.scalars(select(DocumentPage).where(DocumentPage.document_id==case.document_id))}
    for fact in data.facts.values():
        if any(s.page not in pages or normalize(s.quote) not in pages[s.page] for s in fact.sources):
            raise HTTPException(422,'Sumber fakta tidak cocok dengan dokumen.')
    facts={k:v.model_dump() for k,v in data.facts.items()}; result=classify(db,facts)
    db.add(Assessment(case_id=case.id,created_by=user.id,facts=facts,result=result,case_revision=case.revision))
    db.add(Record(case_id=case.id,created_by=user.id,kind='analysis',payload={'note':data.note,'revision':case.revision}))
    case.status='Siap Evaluasi'
    audit(db,user,'regulatory_analysis',case.id,{'matches':len(result)}); db.commit()
    return {'matches':result,'message':'Belum cukup informasi untuk menentukan kecocokan ketentuan.' if not result else 'Penilaian awal memerlukan telaah manusia.'}

@app.post('/api/cases/{case_id}/notes')
def note(case_id:str,data:Note,user:User=Depends(require('review')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); ensure_mutable(db,case)
    if data.kind=='commission_recommendation':
        raise HTTPException(409,'Simpan rekomendasi melalui evaluasi Komdis agar revisi dan hasil telaah tercatat.')
    db.add(Record(case_id=case.id,created_by=user.id,kind=data.kind,payload={'text':data.text}))
    if data.kind=='commission_recommendation': case.status='Rekomendasi Diterbitkan'
    audit(db,user,data.kind,case.id); db.commit(); return {'ok':True}

@app.post('/api/cases/{case_id}/evaluation/draft')
async def evaluation_draft(case_id:str,data:EvaluationDraftRequest,user:User=Depends(require('review')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id);ensure_mutable(db,case)
    current=case_dict(db,case,True)
    if not case.verified: raise HTTPException(409,'Verifikasi fakta BAP sebelum membuat draf evaluasi.')
    if data.expected_revision!=case.revision or data.expected_assessment_id!=current['latest_assessment_id']:
        raise HTTPException(409,'Data berubah. Muat ulang sebelum membuat draf.')
    config=authorized_inference(data)
    options=article_options(db)
    audit_inference_consent(db,user,case.document_id,config);db.commit()
    try: draft=await generate_draft(current,options,config)
    except ValueError as exc: raise HTTPException(422,str(exc))
    db.expire_all();case=get_case(db,case_id);ensure_mutable(db,case)
    updated=case_dict(db,case,True)
    if not case.verified or case.revision!=data.expected_revision or updated['latest_assessment_id']!=data.expected_assessment_id or article_options(db)!=options:
        raise HTTPException(409,'BAP atau regulasi berubah saat AI bekerja. Buat ulang draf dari data terbaru.')
    try: articles=resolve_articles(db,draft['article_ids'])
    except ValueError as exc: raise HTTPException(422,str(exc))
    record=Record(case_id=case.id,created_by=user.id,kind='ai_evaluation_draft',payload={**draft,'revision':case.revision,'assessment_id':updated['latest_assessment_id'],'articles':articles,'provider':config.provider,'model':config.model})
    db.add(record);db.flush();audit(db,user,'evaluation_draft_generated',case.id,{'draft_id':record.id,'revision':case.revision,'provider':config.provider,'model':config.model});db.commit()
    return {**draft,'id':record.id,'revision':case.revision,'assessment_id':updated['latest_assessment_id'],'articles':articles}

@app.post('/api/cases/{case_id}/evaluation')
def evaluate(case_id:str,data:Evaluation,user:User=Depends(require('review')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); ensure_mutable(db,case)
    current=case_dict(db,case,True)
    if data.expected_revision!=case.revision or data.expected_assessment_id!=current['latest_assessment_id']:
        raise HTTPException(409,'Data berubah. Muat ulang dan periksa kembali sebelum menyimpan evaluasi.')
    if len(data.summary)<10: raise HTTPException(422,'Ringkasan evaluasi minimal 10 karakter.')
    if data.outcome=='proceed':
        if not case.verified: raise HTTPException(409,'Verifikasi hasil BAP sebelum melanjutkan ke rekomendasi.')
        if not data.human_reviewed: raise HTTPException(422,'Konfirmasikan bahwa Komdis telah menelaah isi rekomendasi.')
        if len(data.recommendation)<10 or len(data.basis)<10:
            raise HTTPException(422,'Lengkapi rekomendasi dan dasar pertimbangan, minimal 10 karakter masing-masing.')
    try: articles=resolve_articles(db,data.article_ids)
    except ValueError as exc: raise HTTPException(422,str(exc))
    if data.ai_draft_id:
        draft=db.get(Record,data.ai_draft_id)
        if not draft or draft.case_id!=case.id or draft.kind!='ai_evaluation_draft' or draft.payload['revision']!=case.revision or draft.payload['assessment_id']!=current['latest_assessment_id']:
            raise HTTPException(409,'Draf AI sudah tidak sesuai revisi perkara. Buat ulang draf.')
    payload=data.model_dump(exclude={'expected_revision','expected_assessment_id'})
    payload.update(articles=articles,letterhead=read_letterhead(db))
    payload.update(revision=case.revision,assessment_id=current['latest_assessment_id'])
    db.add(Record(case_id=case.id,created_by=user.id,kind='evaluation',payload=payload))
    if data.outcome=='revise': case.verified=False
    case.status='Rekomendasi Siap' if data.outcome=='proceed' else 'Perlu Perbaikan'
    audit(db,user,'komdis_evaluation',case.id,{'outcome':data.outcome,'revision':case.revision})
    db.commit();return case_dict(db,case,True)

@app.get('/api/cases/{case_id}/recommendation')
def recommendation(case_id:str,user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); current=case_dict(db,case,True)
    if not current['recommendation_ready']:
        raise HTTPException(409,'Rekomendasi belum siap. Verifikasi BAP dan simpan evaluasi Lanjutkan untuk revisi serta analisis terbaru.')
    content=generate_recommendation(current,user.name)
    audit(db,user,'recommendation_generated',case.id,{'evaluation_id':current['evaluation']['id'],'revision':case.revision});db.commit()
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'inline; filename="Rekomendasi-{case.number}.pdf"'})

@app.post('/api/cases/{case_id}/attachments')
async def attachment(case_id:str,file:UploadFile=File(...),user:User=Depends(require('upload')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); ensure_mutable(db,case); item_id=uid(); path=settings.storage_path/f'{item_id}.pdf'
    await store_pdf(file,path)
    item=Attachment(id=item_id,case_id=case.id,name=Path(file.filename.replace('\\','/')).name[:255],path=str(path),uploaded_by=user.id)
    db.add(item); audit(db,user,'supporting_document_uploaded',case.id,{'attachment_id':item_id}); db.commit(); return {'id':item_id,'name':item.name}

@app.get('/api/attachments/{item_id}/pdf')
def attachment_pdf(item_id:str,user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    item=db.get(Attachment,item_id)
    if not item: raise HTTPException(404,'Dokumen pendukung tidak ditemukan.')
    get_case(db,item.case_id); audit(db,user,'supporting_document_viewed',item_id); db.commit()
    return FileResponse(item.path,media_type='application/pdf',filename=item.name,content_disposition_type='inline')

@app.post('/api/cases/{case_id}/workflow')
def workflow(case_id:str,data:WorkflowUpdate,user:User=Depends(require('review')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id)
    if not case.verified: raise HTTPException(409,'Verifikasi hasil ekstraksi terlebih dahulu.')
    records=db.scalars(select(Record).where(Record.case_id==case.id,Record.kind=='workflow')).all()
    if data.stage!=len(records): raise HTTPException(409,'Tahapan harus dicatat berurutan dan tidak dapat ditimpa.')
    if data.stage>=10 and not db.scalar(select(Decision).where(Decision.case_id==case.id)):
        raise HTTPException(409,'Catat keputusan resmi oleh pejabat berwenang terlebih dahulu.')
    for item_id in data.attachment_ids:
        item=db.get(Attachment,item_id)
        if not item or item.case_id!=case.id: raise HTTPException(422,'Lampiran harus terkait perkara ini.')
    db.add(Record(case_id=case.id,created_by=user.id,kind='workflow',payload=data.model_dump()))
    if data.stage==7: case.status='Telaah Komisi Disiplin'
    if data.stage==8: case.status='Rekomendasi Diterbitkan'
    if data.stage==9: case.status='Menunggu Keputusan Berwenang'
    audit(db,user,'workflow_updated',case.id,{'stage':data.stage}); db.commit(); return {'ok':True}

@app.post('/api/cases/{case_id}/decisions')
def decision(case_id:str,data:DecisionCreate,user:User=Depends(require('decide')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); ensure_mutable(db,case)
    stages=db.scalars(select(Record).where(Record.case_id==case.id,Record.kind=='workflow')).all()
    if not case.verified or len(stages)<10: raise HTTPException(409,'Selesaikan verifikasi dan pemeriksaan sampai tahap penetapan keputusan.')
    if db.scalar(select(Decision).where(Decision.number==data.number)): raise HTTPException(409,'Nomor keputusan telah digunakan.')
    db.add(Decision(case_id=case.id,created_by=user.id,**data.model_dump())); case.status='Keputusan Resmi Diterbitkan'
    audit(db,user,'official_decision_recorded',case.id,{'number':data.number}); db.commit(); return {'ok':True}

@app.get('/api/cases/{case_id}/report')
def report(case_id:str,user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    case=get_case(db,case_id); content=generate_report(case_dict(db,case,True),user.name)
    audit(db,user,'report_generated',case.id); db.commit()
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'inline; filename="Laporan-{case.number}.pdf"'})

@app.get('/api/regulations')
def regulations(user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    return [{k:getattr(r,k) for k in ('id','title','number','version','effective_date','source_url','verified','created_at')} | builtin_metadata(r.id) | {'articles':[{'id':a.id,'number':a.number,'text':a.text} for a in db.scalars(select(Article).where(Article.regulation_id==r.id).order_by(Article.number))]} for r in db.scalars(select(Regulation).order_by(Regulation.created_at.desc()))]

@app.post('/api/regulations')
async def import_regulation(file:UploadFile=File(...),title:str=Form(...),number:str=Form(...),version:str=Form(...),effective_date:str=Form(...),source_url:str=Form(...),user:User=Depends(require('regulations')),db:DBSession=Depends(get_db)):
    item_id=uid(); path=settings.storage_path/f'{item_id}.pdf'; await store_pdf(file,path)
    try:
        articles=split_articles(extract_pages(path))
        if not articles: raise ValueError('Pasal tidak dapat diindeks otomatis. Periksa PDF berteks dengan penanda Pasal pada baris tersendiri.')
    except Exception as exc:
        path.unlink(missing_ok=True); raise HTTPException(422,str(exc))
    reg=Regulation(id=item_id,title=title,number=number,version=version,effective_date=effective_date,source_url=source_url,path=str(path))
    db.add(reg); db.flush()
    for article_number,text in articles: db.add(Article(regulation_id=reg.id,number=article_number,text=text))
    audit(db,user,'regulation_imported',reg.id,{'version':version,'articles':len(articles)}); db.commit(); return {'id':reg.id,'articles':len(articles)}

@app.get('/api/regulations/{regulation_id}/pdf')
def regulation_pdf(regulation_id:str,user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    reg=db.get(Regulation,regulation_id)
    if not reg: raise HTTPException(404,'Regulasi tidak ditemukan.')
    audit(db,user,'regulation_viewed',reg.id); db.commit()
    return FileResponse(reg.path,media_type='application/pdf',content_disposition_type='inline')

@app.post('/api/regulations/{regulation_id}/verify')
def verify_regulation(regulation_id:str,user:User=Depends(require('regulations')),db:DBSession=Depends(get_db)):
    reg=db.get(Regulation,regulation_id)
    if not reg: raise HTTPException(404,'Regulasi tidak ditemukan.')
    reg.verified=True; audit(db,user,'regulation_verified',reg.id); db.commit(); return {'ok':True}

@app.get('/api/rules')
def rules(user:User=Depends(require('read')),db:DBSession=Depends(get_db)):
    article_map={a.id:a for a in db.scalars(select(Article))}
    return [{k:getattr(r,k) for k in ('id','article_id','paragraph','letter','text','category','sanction','sanction_basis','conditions','related_articles')} | {'regulation_id':article_map[r.article_id].regulation_id,'article_number':article_map[r.article_id].number,'builtin':article_map[r.article_id].regulation_id==BUILTIN_ID} for r in db.scalars(select(Provision))]

@app.post('/api/rules')
def create_rule(data:RuleCreate,user:User=Depends(require('regulations')),db:DBSession=Depends(get_db)):
    article=db.get(Article,data.article_id); sanction_article=db.get(Article,data.sanction_article_id)
    if not article or not sanction_article or article.regulation_id!=sanction_article.regulation_id:
        raise HTTPException(422,'Pasal pelanggaran dan dasar sanksi wajib berada pada versi regulasi yang sama.')
    reg=db.get(Regulation,article.regulation_id)
    if reg.id==BUILTIN_ID: raise HTTPException(409,'Aturan bawaan terikat versi naskah dan tidak dapat ditambah atau ditimpa. Gunakan versi regulasi baru untuk perubahan.')
    if not reg.verified: raise HTTPException(409,'Verifikasi naskah regulasi terlebih dahulu.')
    if normalize(data.text) not in normalize(article.text) or normalize(data.sanction_basis) not in normalize(sanction_article.text):
        raise HTTPException(422,'Kutipan ketentuan dan dasar sanksi harus sama dengan naskah pasal sumber.')
    if not {'conduct','praja_level'}.issubset({c.field for c in data.conditions}):
        raise HTTPException(422,'Aturan wajib mempertimbangkan conduct dan praja_level; tambahkan kondisi akibat/pengulangan sesuai pasal.')
    values=data.model_dump(); values.pop('sanction_article_id')
    rule=Provision(**values,related_articles=[sanction_article.id]); db.add(rule); db.flush()
    audit(db,user,'regulatory_rule_created',rule.id); db.commit(); return {'id':rule.id}

@app.get('/api/audit')
def audit_logs(user:User=Depends(require('users')),db:DBSession=Depends(get_db)):
    return [{k:getattr(a,k) for k in ('id','action','target','detail','created_at','user_id')} for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200))]

if Path('dist').is_dir():
    app.mount('/',StaticFiles(directory='dist',html=True),name='frontend')
