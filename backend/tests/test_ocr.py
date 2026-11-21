import asyncio
import json
from pathlib import Path

import httpx
import pymupdf as fitz
from pydantic import SecretStr
import pytest

from backend.app.services import ocr
from backend.app.config import settings

TEST_KEY='synthetic-fastocr-test-key'

def pdf_with_text(text):
    with fitz.open() as pdf:
        pdf.new_page().insert_text((40,60),text)
        return pdf.tobytes()

@pytest.fixture
def mixed_pdf(tmp_path):
    with fitz.open(stream=pdf_with_text('HALAMAN PINDAI SINTETIS\nNama: Saksi Uji\nNomor BAP: SCAN-01'),filetype='pdf') as source:
        scan=source[0].get_pixmap(dpi=100).tobytes('png')
    path=tmp_path/'mixed.pdf'
    with fitz.open() as pdf:
        pdf.new_page().insert_text((40,60),'HALAMAN DIGITAL ASLI DENGAN TEKS YANG SUDAH TERBACA.\nNomor BAP: NATIVE-01. Nama: Peserta Uji Sintetis.')
        pdf.new_page()
        page=pdf.new_page();page.insert_image(page.rect,stream=scan)
        pdf.save(path)
    return path

def configured(authorized=True):
    return ocr.OCRConfig('fastocr',SecretStr(TEST_KEY),10,authorized)

def mock_sdk(monkeypatch,*,status='completed',output=None,error_status=None):
    actual=ocr.AsyncFastOCR
    captured={'uploads':[],'started':False,'calls':[]}
    output=output if output is not None else pdf_with_text('HALAMAN PINDAI SINTETIS\nNama: Saksi Uji\nNomor BAP: SCAN-01')
    def handler(request):
        captured['calls'].append(str(request.url))
        if request.url.host=='storage.test':
            assert all(TEST_KEY not in value for value in request.headers.values())
            if request.method=='PUT':
                captured['uploads'].append(request.content)
                return httpx.Response(200)
            return httpx.Response(200,content=output,headers={'Content-Type':'application/pdf'})
        assert request.url.host=='api.fastocr.org'
        assert request.headers.get('Authorization')=='Bearer '+TEST_KEY
        if error_status:return httpx.Response(error_status,json={'error':{'code':'unauthorized','message':TEST_KEY+' private document'}})
        path=request.url.path
        if path=='/v1/documents' and request.method=='POST':
            assert json.loads(request.content)['filename']=='sipak-scanned-pages.pdf'
            assert request.headers.get('Idempotency-Key')
            return httpx.Response(201,json={'id':'ocr-test','status':'awaiting_upload','upload_url':'https://storage.test/upload','expires_at':'2026-12-01'})
        if path.endswith('/start'):
            captured['started']=True
            return httpx.Response(200,json={'id':'ocr-test','status':'processing'})
        if path.endswith('/output'):
            return httpx.Response(200,json={'format':'pdf','url':'https://storage.test/result','expires_at':'2026-12-01'})
        return httpx.Response(200,json={'id':'ocr-test','status':status if captured['started'] else 'awaiting_upload','pages_total':1})
    monkeypatch.setattr(ocr,'AsyncFastOCR',lambda **kwargs:actual(transport=httpx.MockTransport(handler),**kwargs))
    return captured

def test_digital_pdf_does_not_use_network(tmp_path,monkeypatch):
    path=tmp_path/'digital.pdf';path.write_bytes(pdf_with_text('DOKUMEN DIGITAL SINTETIS. Nomor BAP: DIGITAL-01. Tidak memerlukan OCR.'))
    monkeypatch.setattr(ocr,'AsyncFastOCR',lambda **kwargs:pytest.fail('Digital PDF must not use FastOCR'))
    pages,used=asyncio.run(ocr.extract_pages(path,configured()))
    assert not used and pages[0]['page']==1 and 'DIGITAL-01' in pages[0]['text']

def test_sdk_fallback_preserves_original_page_numbers_and_only_sends_scanned_pages(mixed_pdf,monkeypatch):
    captured=mock_sdk(monkeypatch)
    pages,used=asyncio.run(ocr.extract_pages(mixed_pdf,configured(),document_id='synthetic-id'))
    assert used and [page['page'] for page in pages]==[1,2,3]
    assert 'NATIVE-01' in pages[0]['text'] and pages[1]['text']=='' and 'SCAN-01' in pages[2]['text']
    assert len(captured['uploads'])==1
    with fitz.open(stream=captured['uploads'][0],filetype='pdf') as submitted:
        assert len(submitted)==1 and submitted[0].get_text()=='' and submitted[0].get_images()

@pytest.mark.parametrize('config,pattern',[(ocr.OCRConfig(),'FASTOCR_API_KEY'),(configured(False),'persetujuan')])
def test_scan_never_leaves_server_without_configuration_and_consent(mixed_pdf,monkeypatch,config,pattern):
    monkeypatch.setattr(ocr,'AsyncFastOCR',lambda **kwargs:pytest.fail('No external upload authorized'))
    with pytest.raises(ValueError,match=pattern):asyncio.run(ocr.extract_pages(mixed_pdf,config))

def test_partial_result_is_not_used(mixed_pdf,monkeypatch):
    captured=mock_sdk(monkeypatch,status='partial')
    with pytest.raises(ValueError,match='parsial'):asyncio.run(ocr.extract_pages(mixed_pdf,configured()))
    assert not any('/output' in url for url in captured['calls'])

@pytest.mark.parametrize('output,pattern',[(pdf_with_text(''), 'belum terbaca'),(b'not a pdf','dapat dibaca')])
def test_unreadable_ocr_output_is_not_used(mixed_pdf,monkeypatch,output,pattern):
    mock_sdk(monkeypatch,output=output)
    with pytest.raises(ValueError,match=pattern):asyncio.run(ocr.extract_pages(mixed_pdf,configured()))

def test_page_count_mismatch_is_rejected(mixed_pdf,monkeypatch):
    with fitz.open() as pdf:
        pdf.new_page();pdf.new_page();output=pdf.tobytes()
    mock_sdk(monkeypatch,output=output)
    with pytest.raises(ValueError,match='Jumlah halaman'):asyncio.run(ocr.extract_pages(mixed_pdf,configured()))

def test_provider_error_never_exposes_key_or_document(mixed_pdf,monkeypatch):
    mock_sdk(monkeypatch,error_status=401)
    with pytest.raises(ValueError) as error:asyncio.run(ocr.extract_pages(mixed_pdf,configured()))
    assert 'API key FastOCR tidak valid' in str(error.value)
    assert TEST_KEY not in str(error.value) and 'private document' not in str(error.value)

def test_public_settings_only_expose_ocr_availability(client,monkeypatch):
    monkeypatch.setattr(settings,'ocr_provider','fastocr');monkeypatch.setattr(settings,'fastocr_api_key',SecretStr(TEST_KEY))
    response=client.get('/api/settings')
    assert response.status_code==200 and response.json()['ocr_provider']=='fastocr' and response.json()['ocr_configured']
    assert TEST_KEY not in response.text

def test_changed_ocr_provider_is_rejected_before_upload(client,pdf_bytes):
    response=client.post('/api/documents',files={'file':('synthetic.pdf',pdf_bytes,'application/pdf')},data={'ocr_consent':'true','expected_ocr_provider':'fastocr'})
    assert response.status_code==409 and client.get('/api/documents').json()==[]

def test_pipeline_stores_original_page_numbers_after_ocr(client,mixed_pdf,monkeypatch):
    from sqlalchemy import select
    from backend.app.database import SessionLocal
    from backend.app.models import DocumentPage,Audit
    from backend.app.schemas import Extraction
    monkeypatch.setattr(settings,'ocr_provider','fastocr');monkeypatch.setattr(settings,'fastocr_api_key',SecretStr(TEST_KEY))
    mock_sdk(monkeypatch)
    async def infer(chunk,**kwargs):
        assert [page['page'] for page in chunk]==[1,3]
        return Extraction.model_validate({'case_information':{'bap_number':'SCAN-01','sources':[{'page':3,'quote':'Nomor BAP: SCAN-01'}]}})
    monkeypatch.setattr('backend.app.services.pipeline.infer',infer)
    response=client.post('/api/documents',files={'file':('mixed.pdf',mixed_pdf.read_bytes(),'application/pdf')},data={'ocr_consent':'true','expected_ocr_provider':'fastocr'})
    assert response.status_code==201,response.text
    document=client.get('/api/documents').json()[0]
    assert document['status']=='Berhasil'
    case=client.get('/api/cases/'+document['case_id']).json()
    assert case['information']['bap_number']=='SCAN-01'
    assert case['information']['sources'][0]['page']==3
    with SessionLocal() as db:
        pages=list(db.scalars(select(DocumentPage).order_by(DocumentPage.number)))
        assert [page.number for page in pages]==[1,2,3] and 'SCAN-01' in pages[2].text
        assert db.scalar(select(Audit).where(Audit.action=='external_ocr_authorized'))
