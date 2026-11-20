from sqlalchemy import select, func
import pytest
from backend.app.database import SessionLocal
from backend.app.models import Regulation, Article, Provision
from backend.app.services.builtin_regulation import (
    BUILTIN_ID, PDF_PATH, bundled_data, seed_builtin_regulation, article_id,
    provisions, paragraph, REFERENCE_ONLY, conduct_label,
)
from backend.app.services.documents import normalize
from backend.app.services.regulations import classify


def facts(reference, **values):
    # Unit matching input only; API tests separately verify BAP source text.
    return {key:{'value':value,'sources':[]} for key,value in {'conduct':reference,**values}.items()}

def complete(db, reference, **values):
    return [m for m in classify(db,facts(reference,**values)) if not m['missing']]

def test_automatic_install_and_idempotence(client):
    response=client.get('/api/regulations'); assert response.status_code==200
    built=[r for r in response.json() if r['builtin']]
    assert len(built)==1
    reg=built[0]
    assert reg['id']==BUILTIN_ID
    assert reg['effective_date']=='2026-03-02'
    assert reg['page_count']==25
    assert [a['number'] for a in reg['articles']]==list(range(1,62))
    assert reg['rule_count']==486
    assert reg['article_pages']['38']==[17,18]
    assert reg['article_pages']['39']==[19]
    assert reg['clause_pages']['Pasal 11 ayat (2) huruf bo']==[10]
    with SessionLocal() as db:
        assert seed_builtin_regulation(db) is False
        db.commit()
        assert db.scalar(select(func.count()).select_from(Article).where(Article.regulation_id==BUILTIN_ID))==61
        assert db.scalar(select(func.count()).select_from(Provision))==486
    pdf=client.get('/api/regulations/'+BUILTIN_ID+'/pdf')
    assert pdf.status_code==200 and pdf.content==PDF_PATH.read_bytes()
    assert 'Cache-Control' in pdf.headers

def test_source_text_and_references_are_exact(client):
    manifest,articles,rules=bundled_data()
    indexed={a['number']:a for a in articles}
    assert '2 Maret 2026' not in indexed[61]['text'] # signature block excluded from the article
    assert 'diundangkan' in indexed[61]['text']
    assert 'BAB VI' not in indexed[59]['text']
    assert 'meninggal dunia' in paragraph(indexed[38]['text'],5)
    for rule in rules:
        number=next(n for n in indexed if article_id(n)==rule['article_id'])
        assert normalize(rule['text']) in normalize(indexed[number]['text'])
        assert rule['related_articles']
        assert rule['sanction_basis']
        assert all(indexed[n]['text'] for n in (35,36,37,38,39))
    reference_only={conduct_label(*ref) for ref in REFERENCE_ONLY}
    assert not any(c['equals'] in reference_only for r in rules for c in r['conditions'] if c['field']=='conduct')

def test_violence_depends_on_level_consequence_and_history(client):
    ref='Pasal 11 ayat (2) huruf bo'
    with SessionLocal() as db:
        unknown=classify(db,facts(ref))
        assert unknown and all(m['sanction'] is None for m in unknown)
        assert classify(db,{})==[]
        a=complete(db,ref,praja_level='Pratama',severe_consequence=False,repeated_serious=False)
        assert len(a)==1 and a[0]['sanction'].startswith('Tahan tingkat')
        b=complete(db,ref,praja_level='Madya',severe_consequence=False,repeated_serious=False)
        assert len(b)==1 and b[0]['sanction']=='Turun tingkat'
        c=complete(db,ref,severe_consequence=True)
        assert len(c)==1 and c[0]['sanction']=='Diberhentikan sebagai Praja'
        d=complete(db,ref,repeated_serious=True)
        assert len(d)==1 and 'Pasal 39 ayat (6)' in d[0]['sanction_basis']

def test_special_alcohol_and_theft_conditions(client):
    with SessionLocal() as db:
        ref='Pasal 11 ayat (2) huruf bp'
        base=complete(db,ref,praja_level='Muda',damage_and_disturbance=False,repeated_serious=False)
        assert len(base)==1 and base[0]['sanction']=='Turun tingkat'
        escalated=complete(db,ref,damage_and_disturbance=True)
        assert len(escalated)==1 and 'Pasal 38 ayat (8)' in escalated[0]['sanction_basis']
        ref='Pasal 11 ayat (2) huruf bq'
        base=complete(db,ref,praja_level='Pratama',peace_with_victim=True,repeated_serious=False)
        assert len(base)==1 and base[0]['sanction'].startswith('Tahan tingkat')
        escalated=complete(db,ref,peace_with_victim=False)
        assert len(escalated)==1 and 'Pasal 38 ayat (11)' in escalated[0]['sanction_basis']

def test_cumulative_and_escalation_rules(client):
    with SessionLocal() as db:
        light=complete(db,'Pasal 19 ayat (1) huruf a')
        assert len(light)==1 and light[0]['category']=='Ringan'
        assert 'Pasal 36 ayat (2)' in light[0]['sanction_basis']
        assert 'kumulatif' in light[0]['sanction']
        assert 'Pasal 39 ayat (1)' in light[0]['sanction_basis']
        ref='Pasal 19 ayat (1) huruf c'
        medium=complete(db,ref,medium_escalation=False)
        assert len(medium)==1 and medium[0]['category']=='Sedang'
        assert 'Pasal 37 ayat (2)' in medium[0]['sanction_basis']
        assert 'Pasal 39 ayat (2)' in medium[0]['sanction_basis']
        high=complete(db,ref,praja_level='Utama',medium_escalation=True)
        assert len(high)==1 and high[0]['sanction']=='Turun tingkat'
        assert 'Pasal 39 ayat (5)' in high[0]['sanction_basis']

def test_additional_proofs_are_required(client):
    with SessionLocal() as db:
        assert not complete(db,'Pasal 7 ayat (2) huruf c',praja_level='Pratama',repeated_serious=False)
        assert complete(db,'Pasal 7 ayat (2) huruf c',praja_level='Pratama',repeated_serious=False,exam_minutes_confirmed=True)
        assert not complete(db,'Pasal 11 ayat (2) huruf br')
        assert complete(db,'Pasal 11 ayat (2) huruf br',screening_or_lab_confirmed=True)
        assert not complete(db,'Pasal 11 ayat (2) huruf ba',medium_escalation=False)
        assert complete(db,'Pasal 11 ayat (2) huruf ba',medium_escalation=False,light_repeat_threshold_met=True)

def test_builtin_rules_cannot_be_modified_from_api(client):
    payload={'article_id':article_id(11),'paragraph':'2','letter':'bo','text':'bo. melakukan kekerasan kepada orang lain;','category':'Berat','sanction':'Tidak sah','sanction_basis':'Naskah buatan tidak sesuai','sanction_article_id':article_id(38),'conditions':[{'field':'conduct','equals':'x'},{'field':'praja_level','equals':'Pratama'}]}
    response=client.post('/api/rules',json=payload)
    assert response.status_code==409 and 'bawaan' in response.json()['detail']

def test_corrupt_packaged_pdf_is_rejected(tmp_path,monkeypatch):
    import backend.app.services.builtin_regulation as module
    corrupt=tmp_path/'corrupt.pdf';corrupt.write_bytes(b'%PDF-corrupted')
    bundled_data.cache_clear()
    monkeypatch.setattr(module,'PDF_PATH',corrupt)
    try:
        with pytest.raises(RuntimeError,match='Checksum'):
            bundled_data()
    finally:
        bundled_data.cache_clear()
