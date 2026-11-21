import time
from sqlalchemy import select
from ..database import SessionLocal
from ..models import Document, DocumentPage, Case, User
from ..security import audit
from ..config import settings
from .documents import chunks
from .extraction import infer, validate_sources, aggregate
from .cases import save_extraction
from .ai_provider import snapshot
from .ocr import extract_pages as extract_with_ocr

async def process_document(document_id,config=None,ocr_config=None):
    config=config or snapshot()
    started = time.monotonic()
    with SessionLocal() as db:
        doc = db.get(Document,document_id)
        user = db.get(User,doc.uploaded_by)
        try:
            doc.status='Sedang Diproses'; doc.stage=2; doc.error=None; db.commit()
            pages,ocr_used=await extract_with_ocr(doc.path,config=ocr_config,document_id=doc.id)
            if ocr_used:audit(db,user,'ocr_completed',doc.id,{'provider':'fastocr','page_count':len(pages)})
            existing=db.scalars(select(DocumentPage).where(DocumentPage.document_id==doc.id)).all()
            for p in existing: db.delete(p)
            for page in pages: db.add(DocumentPage(document_id=doc.id,number=page['page'],text=page['text']))
            doc.stage=3; db.commit()
            results=[]
            for chunk in chunks(pages):
                results.append(validate_sources(await infer(chunk,config=config), chunk))
            doc.stage=4; db.commit()
            extraction=aggregate(results)
            # Legal matching requires reviewed facts and verified rules; never infer sanctions here.
            doc.stage=5; db.commit()
            case = db.scalar(select(Case).where(Case.document_id==doc.id))
            if not case:
                case=Case(number=f'SPK-{time.strftime("%Y")}-{doc.id[:8].upper()}',document_id=doc.id)
                db.add(case); db.flush()
            save_extraction(db,case,extraction)
            doc.status='Berhasil'; doc.stage=6; doc.duration=round(time.monotonic()-started)
            audit(db,user,'extraction_completed',doc.id,{'provider':config.provider,'model':config.model})
            db.commit()
        except Exception as exc:
            db.rollback(); doc=db.get(Document,document_id)
            doc.status='Gagal'
            doc.error=str(exc)[:1500] if isinstance(exc,ValueError) else 'Pemrosesan gagal karena kesalahan layanan. Periksa konfigurasi server lalu coba kembali.'
            doc.duration=round(time.monotonic()-started)
            audit(db,user,'extraction_failed',doc.id,{'error':doc.error}); db.commit()
