"""Opt-in FastOCR fallback with original PDF page numbers preserved."""
import asyncio
from dataclasses import dataclass
from io import BytesIO
import uuid

import pymupdf as fitz
from pydantic import SecretStr
from fastocr_sdk import AsyncFastOCR, FastOCRError, PollingTimeoutError

from ..config import settings
from .documents import normalize

FASTOCR_URL='https://api.fastocr.org'

@dataclass(frozen=True)
class OCRConfig:
    provider: str = 'disabled'
    api_key: SecretStr = SecretStr('')
    timeout: int = 300
    authorized: bool = False

def snapshot(authorized=False):
    ready=settings.ocr_provider=='fastocr' and bool(settings.fastocr_api_key.get_secret_value())
    return OCRConfig('fastocr' if ready else 'disabled',settings.fastocr_api_key,settings.ocr_timeout_seconds,authorized)

def public_config():
    config=snapshot()
    return {'ocr_provider':config.provider,'ocr_configured':config.provider=='fastocr','ocr_endpoint':FASTOCR_URL if config.provider=='fastocr' else ''}

def inspect_pdf(path):
    pages=[];scanned=[]
    with fitz.open(path) as pdf:
        for index,page in enumerate(pdf):
            text=page.get_text(sort=True).strip()
            images=page.get_images(full=True)
            coverage=0
            for image in images:
                for rect in page.get_image_rects(image[0]):
                    coverage=max(coverage,(rect & page.rect).get_area()/max(1,page.rect.get_area()))
            length=len(normalize(text))
            needs_ocr=(length<80 and (images or page.get_drawings())) or (coverage>=.5 and length<400)
            pages.append({'page':index+1,'text':text})
            if needs_ocr:scanned.append(index)
        subset=None
        if scanned:
            with fitz.open() as selected:
                for index in scanned:selected.insert_pdf(pdf,from_page=index,to_page=index)
                subset=selected.tobytes(garbage=4,deflate=True)
    return pages,scanned,subset

class BoundedOutput(BytesIO):
    def write(self,data):
        if self.tell()+len(data)>80*1024*1024:
            raise ValueError('Hasil PDF OCR terlalu besar. Pisahkan dokumen sebelum diproses kembali.')
        return super().write(data)

def output_pages(data,expected):
    try:
        with fitz.open(stream=data,filetype='pdf') as pdf:
            if pdf.needs_pass or len(pdf)!=expected:
                raise ValueError('Jumlah halaman hasil OCR tidak sesuai PDF sumber. Hasil tidak digunakan.')
            pages=[page.get_text(sort=True).strip() for page in pdf]
    except (fitz.FileDataError,fitz.EmptyFileError,RuntimeError):
        raise ValueError('FastOCR tidak mengembalikan PDF yang dapat dibaca.') from None
    if any(len(normalize(text))<20 for text in pages):
        raise ValueError('Sebagian halaman scan belum terbaca oleh OCR. Periksa kualitas scan dan coba kembali.')
    return pages

async def extract_pages(path,config=None,document_id='document'):
    pages,scanned,subset=await asyncio.to_thread(inspect_pdf,path)
    if not scanned:
        if not any(len(normalize(page['text']))>=20 for page in pages):
            raise ValueError('Teks tidak ditemukan dalam PDF. Periksa isi dokumen.')
        return pages,False
    config=config or snapshot()
    if config.provider!='fastocr':
        raise ValueError('PDF berisi halaman scan. Atur FASTOCR_API_KEY pada server untuk mengaktifkan OCR.')
    if not config.authorized:
        raise ValueError('Halaman scan memerlukan persetujuan pengiriman PDF ke FastOCR. Proses ulang dan konfirmasikan penerimanya.')
    try:
        async with AsyncFastOCR(api_key=config.api_key.get_secret_value(),base_url=FASTOCR_URL,timeout=30,transfer_timeout=120,max_retries=2,trust_env=False) as client:
            job=await client.documents.process(subset,filename='sipak-scanned-pages.pdf',idempotency_key=f'sipak-{document_id}-{uuid.uuid4().hex}',timeout=config.timeout)
            if job.is_partial or (job.pages_total is not None and job.pages_total!=len(scanned)):
                raise ValueError('OCR hanya memproses sebagian halaman. Periksa saldo halaman FastOCR lalu proses ulang; hasil parsial tidak digunakan.')
            output=BoundedOutput()
            await client.documents.download_searchable_pdf(job.id,output)
            recognized=await asyncio.to_thread(output_pages,output.getvalue(),len(scanned))
    except PollingTimeoutError:
        raise ValueError('FastOCR melewati batas waktu. Periksa status dokumen pada FastOCR sebelum memproses ulang.') from None
    except FastOCRError as error:
        if error.status_code in (401,403):message='API key FastOCR tidak valid atau tidak memiliki akses.'
        elif error.code=='buy_pages':message='Saldo halaman FastOCR tidak mencukupi. Tambahkan saldo sebelum memproses ulang.'
        elif error.status_code==429:message='Batas permintaan FastOCR tercapai. Coba kembali nanti.'
        else:message='OCR FastOCR belum berhasil. Periksa koneksi, saldo halaman dan kualitas PDF.'
        raise ValueError(message) from None
    for index,text in zip(scanned,recognized):pages[index]['text']=text
    return pages,True
