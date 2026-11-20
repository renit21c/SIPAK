import base64
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from pathlib import Path
from functools import lru_cache
from ..models import ApplicationSetting
from ..schemas import Letterhead

@lru_cache(maxsize=1)
def default_letterhead():
    with Image.open(Path(__file__).resolve().parents[2]/'assets'/'branding'/'logo-ipdn.png') as logo:
        logo.thumbnail((384,384));output=BytesIO();logo.convert('RGBA').save(output,format='PNG')
    return Letterhead(institution_name='INSTITUT PEMERINTAHAN DALAM NEGERI',unit_name='KOMISI DISIPLIN',address='Jl. Ir. Soekarno KM 20, Desa Cibeusi, Kecamatan Jatinangor, Kabupaten Sumedang, Jawa Barat 45363',place='Jatinangor',logo_left='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()).model_dump()

def read_letterhead(db):
    row=db.get(ApplicationSetting,'letterhead')
    return Letterhead.model_validate(row.value if row else default_letterhead()).model_dump()

def normalize_logo(value):
    if not value: return ''
    if not value.startswith(('data:image/png;base64,','data:image/jpeg;base64,')):
        raise ValueError('Logo harus berupa PNG atau JPEG.')
    try:
        raw=base64.b64decode(value.split(',',1)[1],validate=True)
        if len(raw)>350000: raise ValueError('Ukuran logo maksimum 350 KB.')
        with Image.open(BytesIO(raw)) as logo:
            if logo.width>4000 or logo.height>4000: raise ValueError('Dimensi logo maksimum 4000 piksel.')
            logo.load();logo.thumbnail((512,512))
            output=BytesIO();logo.convert('RGBA').save(output,format='PNG')
        return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
    except (UnidentifiedImageError,OSError,base64.binascii.Error,Image.DecompressionBombError):
        raise ValueError('Gambar logo tidak dapat dibaca.') from None

def save_letterhead(db,profile):
    value=profile.model_dump()
    for key in ('logo_left','logo_right'): value[key]=normalize_logo(value[key])
    row=db.get(ApplicationSetting,'letterhead')
    if row: row.value=value
    else: db.add(ApplicationSetting(key='letterhead',value=value))
    return value
