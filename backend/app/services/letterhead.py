import base64
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from pathlib import Path
from functools import lru_cache
from ..models import ApplicationSetting
from ..schemas import Letterhead, LOGO_DATA_URL_MAX_LENGTH

MAX_LOGO_BYTES = 350000
MAX_LEGACY_LOGO_BYTES = 2000000

@lru_cache(maxsize=1)
def default_letterhead():
    with Image.open(Path(__file__).resolve().parents[2]/'assets'/'branding'/'logo-ipdn.png') as logo:
        logo.thumbnail((384,384));output=BytesIO();logo.convert('RGBA').save(output,format='PNG')
    return Letterhead(institution_name='INSTITUT PEMERINTAHAN DALAM NEGERI',unit_name='KOMISI DISIPLIN',address='Jl. Ir. Soekarno KM 20, Desa Cibeusi, Kecamatan Jatinangor, Kabupaten Sumedang, Jawa Barat 45363',place='Jatinangor',logo_left='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()).model_dump()

def read_letterhead(db):
    row=db.get(ApplicationSetting,'letterhead')
    value=dict(row.value) if row else default_letterhead()
    # Older saves validated the upload, but not the larger PNG produced after
    # conversion. Recover those logos before validating the stored profile.
    # Reading keeps the original database value and approved PDF snapshots intact.
    for key in ('logo_left','logo_right'):
        logo=value.get(key,'')
        if isinstance(logo,str) and (len(logo)>LOGO_DATA_URL_MAX_LENGTH or len(logo.split(',',1)[-1])>4*((MAX_LOGO_BYTES+2)//3)):
            value[key]=normalize_logo(logo,legacy=True)
    return Letterhead.model_validate(value).model_dump()

def normalize_logo(value,*,legacy=False):
    if not value: return ''
    if not value.startswith(('data:image/png;base64,','data:image/jpeg;base64,')):
        raise ValueError('Logo harus berupa PNG atau JPEG.')
    try:
        limit=MAX_LEGACY_LOGO_BYTES if legacy else MAX_LOGO_BYTES
        if len(value)>4*((limit+2)//3)+len('data:image/jpeg;base64,'):
            raise ValueError('Ukuran logo maksimum 350 KB.')
        raw=base64.b64decode(value.split(',',1)[1],validate=True)
        if len(raw)>limit: raise ValueError('Ukuran logo maksimum 350 KB.')
        with Image.open(BytesIO(raw)) as logo:
            if logo.width>4000 or logo.height>4000: raise ValueError('Dimensi logo maksimum 4000 piksel.')
            logo.load();logo.thumbnail((512,512))
            image=logo.convert('RGBA')
            # JPEG -> RGBA PNG can grow substantially. Bound the final encoded
            # bytes too, so saving and reading obey the same size constraints.
            while True:
                output=BytesIO();image.save(output,format='PNG',optimize=True)
                if len(output.getvalue())<=MAX_LOGO_BYTES:break
                image.thumbnail((max(1,int(image.width*.8)),max(1,int(image.height*.8))))
        return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
    except (UnidentifiedImageError,OSError,base64.binascii.Error,Image.DecompressionBombError):
        raise ValueError('Gambar logo tidak dapat dibaca.') from None

def save_letterhead(db,profile):
    value=profile.model_dump()
    for key in ('logo_left','logo_right'): value[key]=normalize_logo(value[key])
    value=Letterhead.model_validate(value).model_dump()
    row=db.get(ApplicationSetting,'letterhead')
    if row: row.value=value
    else: db.add(ApplicationSetting(key='letterhead',value=value))
    return value
