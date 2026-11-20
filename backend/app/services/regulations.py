import re
from sqlalchemy import select
from ..models import Article, Regulation, Provision
from .documents import normalize
from .builtin_regulation import BUILTIN_ID, builtin_clause_pages, conduct_label

def split_articles(pages):
    text='\n\n'.join(p['text'] for p in pages)
    matches=list(re.finditer(r'(?m)^\s*Pasal\s+(\d+)\s*$',text))
    return [(int(m.group(1)),text[m.start():matches[i+1].start() if i+1<len(matches) else len(text)].strip()) for i,m in enumerate(matches)]

def classify(db, facts):
    matches=[]
    articles={a.id:a for a in db.scalars(select(Article))}
    regulations={r.id:r for r in db.scalars(select(Regulation))}
    for rule in db.scalars(select(Provision)):
        article=articles[rule.article_id]
        reg=regulations[article.regulation_id]
        if not reg.verified: continue
        if reg.id==BUILTIN_ID and 'conduct' not in facts: continue
        missing=[]; mismatch=False
        for condition in rule.conditions:
            fact=facts.get(condition['field'])
            if fact is None: missing.append(condition['field'])
            elif type(fact['value']) is not type(condition['equals']) or fact['value']!=condition['equals']:
                mismatch=True; break
        if mismatch: continue
        entry={'rule_id':rule.id,'regulation_id':reg.id,'version':reg.version,'article':article.number,'paragraph':rule.paragraph,'letter':rule.letter,'quote':rule.text,'sanction_basis':rule.sanction_basis,'category':rule.category if not missing else None,'sanction':rule.sanction if not missing else None,'conditions':rule.conditions,'missing':missing,'status':'Potensi kecocokan — perlu telaah manusia' if not missing else 'Belum cukup informasi untuk menentukan kecocokan ketentuan.','sources':[s for key in [c['field'] for c in rule.conditions] for s in facts.get(key,{}).get('sources',[])]}
        if reg.id==BUILTIN_ID:
            entry['regulation_pages']=builtin_clause_pages().get(conduct_label(article.number,int(rule.paragraph),rule.letter),[])
        matches.append(entry)
    return matches
