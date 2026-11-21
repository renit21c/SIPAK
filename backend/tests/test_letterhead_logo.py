import base64
from io import BytesIO
import random

from PIL import Image
import pytest

from backend.app.database import SessionLocal
from backend.app.models import ApplicationSetting
from backend.app.schemas import Letterhead, LOGO_DATA_URL_MAX_LENGTH
from backend.app.services.letterhead import MAX_LOGO_BYTES, normalize_logo
from backend.tests.test_recommendation import evaluation
from backend.tests.test_sipak import verify


@pytest.fixture(scope='module')
def expanding_logo():
    # A valid small JPEG expands past the old limit when saved as RGBA PNG.
    image=Image.frombytes('RGB',(512,512),random.Random(17).randbytes(512*512*3))
    upload=BytesIO();image.save(upload,format='JPEG',quality=80)
    with Image.open(BytesIO(upload.getvalue())) as decoded:
        old=BytesIO();decoded.convert('RGBA').save(old,format='PNG')
    jpeg='data:image/jpeg;base64,'+base64.b64encode(upload.getvalue()).decode()
    legacy='data:image/png;base64,'+base64.b64encode(old.getvalue()).decode()
    assert len(upload.getvalue())<MAX_LOGO_BYTES
    assert len(jpeg)<LOGO_DATA_URL_MAX_LENGTH<len(legacy)
    return jpeg,legacy


def assert_usable_logo(value):
    assert value.startswith('data:image/png;base64,')
    assert len(value)<=LOGO_DATA_URL_MAX_LENGTH
    raw=base64.b64decode(value.split(',',1)[1],validate=True)
    assert len(raw)<=MAX_LOGO_BYTES
    with Image.open(BytesIO(raw)) as image:
        image.load()
        assert 1<image.width<=512 and 1<image.height<=512
        assert image.mode=='RGBA'


def test_jpeg_conversion_is_bounded_and_can_be_saved_again(client,expanding_logo):
    profile=client.get('/api/settings/letterhead').json()
    response=client.put('/api/settings/letterhead',json={**profile,'logo_right':expanding_logo[0]})
    assert response.status_code==200,response.text
    result=response.json();assert_usable_logo(result['logo_right'])
    assert client.get('/api/settings/letterhead').json()==result
    assert client.put('/api/settings/letterhead',json=result).status_code==200


def test_existing_oversized_logos_recover_without_losing_profile(client,expanding_logo):
    original={**client.get('/api/settings/letterhead').json(),'unit_name':'KOMDIS UJI PEMULIHAN','logo_right':expanding_logo[1]}
    with SessionLocal() as db:
        db.add(ApplicationSetting(key='letterhead',value=original));db.commit()
    response=client.get('/api/settings/letterhead')
    assert response.status_code==200,response.text
    recovered=response.json();Letterhead.model_validate(recovered)
    assert recovered['unit_name']==original['unit_name']
    assert recovered['address']==original['address']
    assert recovered['logo_left']==original['logo_left']
    assert_usable_logo(recovered['logo_right'])
    with SessionLocal() as db:
        assert db.get(ApplicationSetting,'letterhead').value==original
    assert client.put('/api/settings/letterhead',json=recovered).status_code==200
    assert client.get('/api/settings/letterhead').status_code==200


def test_legacy_logo_does_not_block_evaluation_or_pdf(case,client,expanding_logo):
    current=verify(client,case)
    profile=client.get('/api/settings/letterhead').json()
    with SessionLocal() as db:
        db.add(ApplicationSetting(key='letterhead',value={**profile,'logo_right':expanding_logo[1]}));db.commit()
    response=client.post('/api/cases/'+current['id']+'/evaluation',json=evaluation(current))
    assert response.status_code==200,response.text
    saved=response.json()['evaluation']['payload']['letterhead']
    assert_usable_logo(saved['logo_right'])
    pdf=client.get('/api/cases/'+current['id']+'/recommendation')
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')


def test_oversized_new_uploads_remain_rejected(expanding_logo):
    with pytest.raises(ValueError,match='350 KB'):
        normalize_logo(expanding_logo[1])
