"""Provider configuration and transport. Secrets never enter API responses/audit."""
import copy
import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import SecretStr, ValidationError
from dotenv import set_key
import httpx
from ..config import settings
from ..schemas import Extraction

OPENROUTER_URL='https://openrouter.ai/api/v1'
EXTRACTION_MAX_TOKENS=6000
CONFIG_ENV_PATH=Path('.env')
CONFIG_LOCK=threading.RLock()

@dataclass(frozen=True)
class InferenceConfig:
    provider: str
    model: str
    api_key: SecretStr = field(repr=False)
    timeout: int = 180
    external_authorized: bool = False

    @property
    def external(self): return self.provider=='openrouter'

def snapshot(authorized=False):
    with CONFIG_LOCK:
        return InferenceConfig(provider=settings.ai_provider,model=settings.ai_model if settings.ai_provider=='openrouter' else settings.ollama_model,api_key=settings.openrouter_api_key,timeout=settings.ai_timeout_seconds,external_authorized=authorized)

def public_config():
    config=snapshot()
    return {'ai_provider':config.provider,'ai_external':config.external,'ai_provider_label':'OpenRouter' if config.external else 'Ollama','ai_endpoint':OPENROUTER_URL if config.external else settings.ollama_url,'model':config.model,'ai_configured':bool(config.model and (config.api_key.get_secret_value() if config.external else True)),'api_key_configured':bool(config.api_key.get_secret_value()),'ai_connected':False}

def save_configuration(provider,model,key=None,clear_key=False):
    if provider not in ('openrouter','ollama'): raise ValueError('Provider tidak didukung.')
    if key is not None:
        raw=key.get_secret_value()
        if len(raw)>4096 or any(c.isspace() for c in raw): raise ValueError('Format API key tidak valid.')
    with CONFIG_LOCK:
        path=CONFIG_ENV_PATH
        if path.is_symlink(): raise ValueError('Konfigurasi melalui symlink tidak didukung.')
        updates={'AI_PROVIDER':provider,'AI_MODEL':model} if provider=='openrouter' else {'AI_PROVIDER':provider,'OLLAMA_MODEL':model}
        if clear_key: updates['OPENROUTER_API_KEY']=''
        elif key and key.get_secret_value(): updates['OPENROUTER_API_KEY']=key.get_secret_value()
        temporary=None
        try:
            fd,temporary=tempfile.mkstemp(prefix='.sipak-config-',suffix='.env',dir=path.parent)
            with os.fdopen(fd,'w',encoding='utf-8') as output:
                output.write(path.read_text(encoding='utf-8') if path.exists() else '')
            for name,value in updates.items(): set_key(temporary,name,value,quote_mode='always')
            os.replace(temporary,path)
            temporary=None
        except OSError:
            raise ValueError('Konfigurasi tidak dapat disimpan. Periksa izin .env pada server.') from None
        finally:
            if temporary: Path(temporary).unlink(missing_ok=True)
        settings.ai_provider=provider
        if provider=='openrouter': settings.ai_model=model
        else: settings.ollama_model=model
        if 'OPENROUTER_API_KEY' in updates: settings.openrouter_api_key=SecretStr(updates['OPENROUTER_API_KEY'])
        # Keep managed environment variables consistent for an in-process reload.
        for name,value in updates.items(): os.environ[name]=value
    return public_config()

def ensure_ready(config):
    if not config.model: raise ValueError('Pilih model AI di Pengaturan terlebih dahulu.')
    if config.external and not config.api_key.get_secret_value(): raise ValueError('API key OpenRouter belum diisi pada Pengaturan.')
    if config.external and not config.external_authorized: raise ValueError('Persetujuan pengiriman isi BAP ke OpenRouter diperlukan untuk dokumen ini.')

def strict_schema(output_model=Extraction):
    schema=copy.deepcopy(output_model.model_json_schema())
    def visit(value):
        if isinstance(value,dict):
            value.pop('default',None)
            if value.get('type')=='object' and 'properties' in value:
                value['required']=list(value['properties'])
                value['additionalProperties']=False
            for item in value.values(): visit(item)
        elif isinstance(value,list):
            for item in value: visit(item)
    visit(schema)
    return schema

def http_error(status):
    return {401:'API key OpenRouter tidak valid.',402:'Saldo atau kredit OpenRouter tidak cukup.',403:'OpenRouter menolak akses model atau kebijakan akun.',404:'Model OpenRouter tidak ditemukan.',408:'Provider AI melewati batas waktu.',429:'Batas permintaan API tercapai. Coba kembali nanti.'}.get(status,f'OpenRouter mengembalikan HTTP {status}. Periksa dukungan JSON Schema, model, dan kebijakan routing akun.')

async def infer_openrouter(chunk,system,config,output_model=Extraction,schema_name='bap_extraction'):
    ensure_ready(config)
    payload={'model':config.model,'stream':False,'temperature':0,'max_tokens':EXTRACTION_MAX_TOKENS,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(chunk,ensure_ascii=False)}],'response_format':{'type':'json_schema','json_schema':{'name':schema_name,'strict':True,'schema':strict_schema(output_model)}},'provider':{'require_parameters':True,'data_collection':'deny','zdr':True,'allow_fallbacks':False}}
    # Nemotron Super VL thinks by default. For factual extraction, reserve the
    # existing output budget for the JSON rather than hidden reasoning tokens.
    # Scope this override to the verified model; other models may require thinking.
    if config.model.removesuffix(':free')=='nvidia/nemotron-3.5-super-vl':
        payload['reasoning']={'enabled':False}
    try:
        async with httpx.AsyncClient(timeout=config.timeout,trust_env=False,follow_redirects=False) as client:
            response=await client.post(OPENROUTER_URL+'/chat/completions',headers={'Authorization':'Bearer '+config.api_key.get_secret_value(),'X-OpenRouter-Title':'SIPAK'},json=payload)
            if response.status_code!=200: raise ValueError(http_error(response.status_code))
            data=response.json()
            if data.get('error'): raise ValueError('OpenRouter gagal menghasilkan respons. Periksa status model dan kredit akun.')
            choice=data['choices'][0]
            if choice.get('finish_reason')=='content_filter' or choice.get('message',{}).get('refusal'):
                raise ValueError('Model menolak pemrosesan dokumen. Hasil ekstraksi tidak disimpan. Periksa kebijakan model atau pilih model lain yang sesuai.')
            if choice.get('finish_reason')=='length':
                usage=data.get('usage') or {}
                details=usage.get('completion_tokens_details') or {}
                reasoning=details.get('reasoning_tokens')
                hint=f' Sebanyak {reasoning} token digunakan untuk thinking.' if type(reasoning) is int and 0<reasoning<=10000000 else ''
                raise ValueError(f'Respons AI mencapai batas {EXTRACTION_MAX_TOKENS} token sebelum JSON selesai.{hint} Hasil parsial tidak disimpan. Kurangi panjang BAP per unggahan atau pilih model yang dapat menghasilkan JSON ringkas.')
            if choice.get('finish_reason')!='stop':
                raise ValueError('Model berhenti tanpa jawaban final yang lengkap. Hasil ekstraksi tidak disimpan. Coba kembali atau periksa kesesuaian model.')
            return output_model.model_validate_json(choice['message']['content'])
    except httpx.TimeoutException:
        raise ValueError('API AI melewati batas waktu. Coba kembali nanti.') from None
    except httpx.HTTPError:
        raise ValueError('Koneksi ke OpenRouter gagal. Periksa jaringan server.') from None
    except (ValidationError,KeyError,IndexError,TypeError,AttributeError,json.JSONDecodeError):
        raise ValueError('Respons OpenRouter tidak sesuai skema ekstraksi. Pilih model yang mendukung structured outputs.') from None

async def check_openrouter():
    """Metadata-only check: never send document text or run paid inference here."""
    config=snapshot()
    if not config.api_key.get_secret_value(): raise ValueError('API key OpenRouter belum diisi.')
    try:
        async with httpx.AsyncClient(timeout=15,trust_env=False,follow_redirects=False) as client:
            auth=await client.get(OPENROUTER_URL+'/key',headers={'Authorization':'Bearer '+config.api_key.get_secret_value()})
            if auth.status_code!=200: raise ValueError(http_error(auth.status_code))
            response=await client.get(OPENROUTER_URL+'/models')
            if response.status_code!=200: raise ValueError('Daftar model OpenRouter belum dapat diambil.')
            models=[{'id':m['id'],'name':m.get('name',m['id'])} for m in response.json().get('data',[]) if 'structured_outputs' in m.get('supported_parameters',[])]
            return {'ai_connected':True,'available_models':models,'model_available':any(m['id']==config.model for m in models),'message':'API key valid. Pemeriksaan ini tidak mengirim isi BAP.'}
    except httpx.HTTPError:
        raise ValueError('Koneksi ke OpenRouter gagal.') from None
    except (KeyError,TypeError,json.JSONDecodeError):
        raise ValueError('Daftar model OpenRouter tidak dapat dibaca.') from None
