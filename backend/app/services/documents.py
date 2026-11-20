import re
from pathlib import Path
import pymupdf as fitz
from fastapi import HTTPException, UploadFile
from ..config import settings

def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()

async def store_pdf(file: UploadFile, path: Path):
    size = 0
    try:
        with path.open('wb') as out:
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, f'Maksimum ukuran PDF {settings.max_upload_mb} MB.')
                out.write(block)
        if not file.filename or not file.filename.lower().endswith('.pdf') or path.read_bytes()[:5] != b'%PDF-':
            raise HTTPException(400, 'Unggah file PDF yang valid.')
        with fitz.open(path) as pdf:
            if pdf.needs_pass: raise HTTPException(400, 'PDF terkunci. Hapus kata sandi terlebih dahulu.')
            if not 1 <= len(pdf) <= 300: raise HTTPException(400, 'PDF harus berisi 1–300 halaman.')
            pages = len(pdf)
        return size, pages
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(400, 'File PDF rusak atau tidak dapat dibaca.')

def extract_pages(path):
    with fitz.open(path) as pdf:
        pages = [{'page':i+1,'text':re.sub(r'[ \t]+',' ',p.get_text(sort=True)).strip()} for i,p in enumerate(pdf)]
    if not any(len(normalize(p['text'])) >= 20 for p in pages):
        raise ValueError('Teks tidak ditemukan. PDF hasil pindai memerlukan OCR yang belum diaktifkan.')
    return pages

def chunks(pages, max_chars=10000):
    batch, length = [], 0
    for page in pages:
        text = page['text']
        # Split with overlap so names and events crossing a boundary remain available.
        for start in range(0, len(text), max_chars-500):
            fragment = {'page':page['page'],'text':text[start:start+max_chars]}
            if batch and length + len(fragment['text']) > max_chars:
                yield batch
                batch, length = [], 0
            batch.append(fragment)
            length += len(fragment['text'])
    if batch: yield batch
