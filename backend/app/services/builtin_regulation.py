"""Versioned local regulation and conservative, source-linked matching rules.

The user's supplied PDF is data, never an instruction source. Every generated rule
retains its conduct wording and the exact sanction paragraphs from that PDF.
"""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import select
from ..models import Regulation, Article, Provision
from ..security import audit
from .documents import extract_pages, normalize

ASSET_ROOT = Path(__file__).resolve().parents[2] / 'assets' / 'regulations'
PDF_PATH = ASSET_ROOT / 'permendagri-8-2026.pdf'
MANIFEST_PATH = ASSET_ROOT / 'permendagri-8-2026.json'
NAMESPACE = UUID('77354d14-9343-4d8c-a83b-250d753d9b40')
LEVELS = ('Pratama', 'Muda', 'Madya', 'Utama')
# These provisions remain fully readable in the reference PDF and article index.
# Do not automate educational outcomes based on health, pregnancy, marital status,
# sexual life or orientation. The matcher covers act-based disciplinary conduct.
REFERENCE_ONLY = {(11, 2, letter) for letter in ('bv', 'bx', 'by', 'bz', 'ca')}

def stable_id(key):
    return str(uuid5(NAMESPACE, key))

def article_id(number):
    return stable_id(f'2c3b9ea6b80c:article:{number}')

BUILTIN_ID = stable_id('2c3b9ea6b80c:regulation')

def parse_articles(pages):
    """Strip only standalone printed page numbers; retain page breaks and wording."""
    parts=[]; spans=[]; offset=0
    for page in pages:
        cleaned=re.sub(r'(?m)^\s*-\s*\d+\s*-\s*$', '', page['text'])
        parts.append(cleaned)
        spans.append((offset,offset+len(cleaned),page['page']))
        offset+=len(cleaned)+2
    text='\n\n'.join(parts)
    headings=list(re.finditer(r'(?m)^[ \t]*Pasal[ \t]+(\d+)[ \t]*$',text))
    articles=[]
    for i,heading in enumerate(headings):
        end=headings[i+1].start() if i+1<len(headings) else len(text)
        body=text[heading.start():end]
        # Chapter/section titles belong to the next provision, not the previous one.
        boundary=re.search(r'(?m)^[ \t]*(?:BAB [IVXLCDM]+|Bagian \w+|Paragraf \d+)[ \t]*$',body)
        if boundary: end=heading.start()+boundary.start(); body=body[:boundary.start()]
        if int(heading.group(1))==61:
            close=re.search(r'(?m)^\s*Agar\s+setiap\s+orang',body)
            if close: end=heading.start()+close.start(); body=body[:close.start()]
        end=heading.start()+len(body.rstrip())
        used=[page for start,stop,page in spans if start<end and stop>heading.start()]
        articles.append({'number':int(heading.group(1)),'text':body.strip(),'pages':used})
    return articles

def paragraph(text,number):
    pattern=rf'(?ms)^\({number}\)[ \t].*?(?=^\(\d+\)[ \t]|\Z)'
    match=re.search(pattern,text)
    if not match: raise ValueError(f'Ayat ({number}) tidak ditemukan dalam naskah bawaan.')
    return match.group().strip()

def provisions(article):
    """Return clauses, including paragraphs without lettered subclauses."""
    text=article['text']; starts=list(re.finditer(r'(?m)^\((\d+)\)[ \t]',text))
    result={}
    for i,start in enumerate(starts):
        part=text[start.start():starts[i+1].start() if i+1<len(starts) else len(text)].strip()
        letters=list(re.finditer(r'(?m)^[ \t]*([a-z]{1,2})\.[ \t]+',part))
        if letters:
            for j,letter in enumerate(letters):
                result[(int(start.group(1)),letter.group(1))]=part[letter.start():letters[j+1].start() if j+1<len(letters) else len(part)].strip()
        else: result[(int(start.group(1)),'')]=part
    return result

def letter_range(first,last):
    def value(s):
        n=0
        for c in s: n=n*26+ord(c)-96
        return n
    def label(n):
        result=''
        while n:
            n,r=divmod(n-1,26); result=chr(97+r)+result
        return result
    return [label(n) for n in range(value(first),value(last)+1)]

def conduct_label(number,para,letter):
    return f'Pasal {number} ayat ({para})'+(f' huruf {letter}' if letter else '')

def generated_rules(articles):
    indexed={a['number']:a for a in articles}; clauses={n:provisions(a) for n,a in indexed.items()}
    rules=[]
    def add(ref,category,sanction,basis_article,basis_paragraph,conditions,extra_basis=()):
        if ref in REFERENCE_ONLY: return
        n,p,l=ref
        clause=clauses[n].get((p,l))
        if not clause: raise ValueError(f'Ketentuan sumber tidak ditemukan: {ref}')
        label=conduct_label(*ref)
        all_conditions=[{'field':'conduct','equals':label}]+conditions
        basis_refs=[(basis_article,basis_paragraph),*extra_basis]
        basis='\n\n'.join(f'Pasal {a} ayat ({b})\n{paragraph(indexed[a]["text"],b)}' for a,b in dict.fromkeys(basis_refs))
        key=json.dumps([ref,category,sanction,basis_refs,all_conditions],sort_keys=True)
        rules.append({'id':stable_id('rule:'+key),'article_id':article_id(n),'paragraph':str(p),'letter':l,'text':clause,'category':category,'sanction':sanction,'sanction_basis':basis,'conditions':all_conditions,'related_articles':list(dict.fromkeys(article_id(a) for a,_ in basis_refs))})
    def level_condition(level): return {'field':'praja_level','equals':level}
    def flag(name,value): return {'field':name,'equals':value}
    def refs(n,p,letters): return [(n,p,l) for l in letters]
    light=(refs(7,1,['a','b'])+refs(9,1,['a','b'])+refs(11,1,letter_range('a','r'))+refs(15,1,['a','b'])+refs(17,1,['a','b'])+[(21,1,'')]+refs(11,2,letter_range('a','p'))+[(15,2,'')]+[(17,2,'a')]+refs(19,1,['a','b'])+refs(21,2,['a','b']))
    medium=(refs(7,1,['c','d'])+refs(9,1,['c','d'])+refs(11,1,letter_range('s','ae'))+refs(7,2,['a','b'])+refs(9,2,['a','b','c'])+refs(11,2,letter_range('q','bc'))+refs(17,2,['b','c'])+[(19,1,'c')])
    # Every sanction in the light/medium category is cumulative (39(1),(2)).
    for ref in light:
        obligation=ref[1]==1 and ref[0]!=19
        add(ref,'Ringan','Teguran lisan; pemberian tugas dan pembinaan fisik (kumulatif)',36,1 if obligation else 2,[],[(35,1),(39,1),(39,3)])
    for ref in medium:
        obligation=ref[1]==1 and ref[0]!=19
        proof=[flag('light_repeat_threshold_met',True)] if ref==(11,2,'ba') else []
        add(ref,'Sedang','Teguran tertulis; pengurangan nilai kepribadian; tugas khusus yang mendidik (kumulatif)',37,1 if obligation else 2,[*proof,flag('medium_escalation',False)],[(35,2),(39,2),(39,3)])
        for level in LEVELS:
            sanction='Tahan tingkat; dipulangkan kepada orang tua sebagai cuti akademik' if level=='Pratama' else 'Turun tingkat'
            extras=[(37,1 if obligation else 2),(35,3)]+([(39,7)] if level=='Pratama' else [])
            add(ref,'Berat',sanction,39,4 if level=='Pratama' else 5,[level_condition(level),*proof,flag('medium_escalation',True)],extras)
    ordinary=(refs(11,1,['af','ag'])+[(7,2,'c'),(9,2,'d')]+refs(11,2,letter_range('bd','bn'))+[(19,1,'d'),(11,2,'bo'),(11,2,'bp'),(11,2,'bq')])
    for ref in ordinary:
        special=[]
        if ref==(11,2,'bo'): special=[flag('severe_consequence',False)]
        if ref==(11,2,'bp'): special=[flag('damage_and_disturbance',False)]
        if ref==(11,2,'bq'): special=[flag('peace_with_victim',True)]
        if ref in ((7,2,'c'),(9,2,'d')): special=[flag('exam_minutes_confirmed',True)]
        if ref==(11,2,'bj'): special=[flag('absence_threshold_met',True)]
        for level in LEVELS:
            if ref[1]==1: basis=1 if level=='Pratama' else 3
            elif ref==(11,2,'bp'): basis=6 if level=='Pratama' else 7
            elif ref==(11,2,'bq'): basis=9 if level=='Pratama' else 10
            else: basis=2 if level=='Pratama' else 4
            sanction='Tahan tingkat; dipulangkan kepada orang tua sebagai cuti akademik' if level=='Pratama' else 'Turun tingkat'
            add(ref,'Berat',sanction,38,basis,[level_condition(level),*special,flag('repeated_serious',False)],[(35,3),(39,6)]+([(39,7)] if level=='Pratama' else []))
        add(ref,'Berat','Diberhentikan sebagai Praja',39,6,[flag('repeated_serious',True)],[(38,1 if ref[1]==1 else 6 if ref==(11,2,'bp') else 9 if ref==(11,2,'bq') else 2),(35,3)])
    dismissal=refs(7,2,letter_range('d','g'))+refs(9,2,['e','f','g'])+refs(11,2,letter_range('br','ch'))
    for ref in dismissal:
        proof=[flag('screening_or_lab_confirmed',True)] if ref==(11,2,'br') else []
        add(ref,'Berat','Diberhentikan sebagai Praja',38,5,proof,[(35,3)])
    add((11,2,'bo'),'Berat','Diberhentikan sebagai Praja',38,5,[flag('severe_consequence',True)],[(35,3)])
    add((11,2,'bp'),'Berat','Diberhentikan sebagai Praja',38,8,[flag('damage_and_disturbance',True)],[(35,3)])
    add((11,2,'bq'),'Berat','Diberhentikan sebagai Praja',38,11,[flag('peace_with_victim',False)],[(35,3)])
    return rules

@lru_cache(maxsize=1)
def bundled_data():
    manifest=json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    if hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()!=manifest['sha256']:
        raise RuntimeError('Checksum naskah regulasi bawaan berubah. Pulihkan PDF sumber sebelum menjalankan server.')
    pages=extract_pages(PDF_PATH); articles=parse_articles(pages)
    if len(pages)!=manifest['page_count'] or [a['number'] for a in articles]!=list(range(1,manifest['article_count']+1)):
        raise RuntimeError('Indeks regulasi bawaan tidak lengkap. Startup dihentikan agar tidak memakai basis hukum parsial.')
    return manifest,articles,generated_rules(articles)

def seed_builtin_regulation(db):
    manifest,articles,rules=bundled_data()
    if db.get(Regulation,BUILTIN_ID): return False
    db.add(Regulation(id=BUILTIN_ID,title=manifest['title'],number=manifest['number'],version=manifest['version'],effective_date=manifest['effective_date'],source_url=manifest['reference_url'],path=str(PDF_PATH),verified=True))
    db.flush()
    for a in articles: db.add(Article(id=article_id(a['number']),regulation_id=BUILTIN_ID,number=a['number'],text=a['text']))
    db.flush()
    for rule in rules: db.add(Provision(**rule))
    audit(db,None,'builtin_regulation_installed',BUILTIN_ID,{'sha256':manifest['sha256'],'articles':len(articles),'rules':len(rules),'source':manifest['source']})
    return True

@lru_cache(maxsize=1)
def builtin_clause_pages():
    """Locate the clause itself, rather than linking every clause to article start."""
    _,articles,rules=bundled_data()
    indexed={a['number']:a for a in articles}
    original=extract_pages(PDF_PATH)
    page_text={p['page']:normalize(re.sub(r'(?m)^\s*-\s*\d+\s*-\s*$','',p['text'])) for p in original}
    located={}
    for rule in rules:
        ref=next(c['equals'] for c in rule['conditions'] if c['field']=='conduct')
        if ref in located: continue
        n=next(n for n in indexed if article_id(n)==rule['article_id'])
        pages=indexed[n]['pages'];parts=[];spans=[];offset=0
        for number in pages:
            part=page_text[number];parts.append(part);spans.append((offset,offset+len(part),number));offset+=len(part)+1
        needle=normalize(rule['text']);start=' '.join(parts).find(needle)
        if start<0: raise RuntimeError(f'Halaman sumber ketentuan bawaan tidak ditemukan: {ref}')
        end=start+len(needle)
        located[ref]=[number for a,b,number in spans if a<end and b>start]
    return located

def builtin_metadata(regulation_id):
    if regulation_id!=BUILTIN_ID: return {'builtin':False}
    manifest,articles,rules=bundled_data()
    return {'builtin':True,'source':manifest['source'],'sha256':manifest['sha256'],'page_count':manifest['page_count'],'rule_count':len(rules),'article_pages':{str(a['number']):a['pages'] for a in articles},'clause_pages':builtin_clause_pages(),'reference_only':[conduct_label(*ref) for ref in sorted(REFERENCE_ONLY)]}
