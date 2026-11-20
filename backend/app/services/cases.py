from sqlalchemy import select, delete
from ..models import Entity, Source, Case, Document, Record, Assessment, Decision, Attachment, User
from ..database import now
from ..schemas import Extraction

def save_extraction(db, case, extraction):
    old = db.scalars(select(Entity).where(Entity.case_id==case.id)).all()
    for item in old:
        db.execute(delete(Source).where(Source.entity_id==item.id))
        db.delete(item)
    for kind, value in extraction.model_dump().items():
        values = [value] if kind in ('case_information','missing_information') else value
        for item in values:
            payload = dict(item) if isinstance(item,dict) else {'items':item}
            sources = payload.pop('sources', [])
            entity = Entity(case_id=case.id,kind=kind,value=payload)
            db.add(entity)
            db.flush()
            for source in sources:
                db.add(Source(entity_id=entity.id,**source))

def read_extraction(db, case):
    data = Extraction().model_dump()
    for entity in db.scalars(select(Entity).where(Entity.case_id==case.id)):
        if entity.kind=='missing_information': data[entity.kind]=entity.value['items']; continue
        item = dict(entity.value)
        item['sources']=[{'page':s.page,'quote':s.quote} for s in db.scalars(select(Source).where(Source.entity_id==entity.id))]
        if entity.kind=='case_information': data[entity.kind]=item
        else: data[entity.kind].append(item)
    return data

def document_dict(d):
    return {k:getattr(d,k) for k in ('id','name','size','page_count','status','stage','error','duration','created_at','uploaded_by')}

def case_dict(db, case, detail=False):
    extraction = read_extraction(db,case)
    doc = db.get(Document,case.document_id)
    assessments = db.scalars(select(Assessment).where(Assessment.case_id==case.id).order_by(Assessment.created_at.desc())).all()
    latest = assessments[0] if assessments else None
    result = latest.result if latest and latest.case_revision==case.revision else []
    output = {'id':case.id,'number':case.number,'status':case.status,'verified':case.verified,'revision':case.revision,'created_at':case.created_at,'document':document_dict(doc),'information':extraction['case_information'],'persons':extraction['involved_persons'],'analysis':result}
    if detail:
        output['extraction']=extraction
        output['records']=[{'id':r.id,'kind':r.kind,'payload':r.payload,'created_at':r.created_at,'created_by':db.get(User,r.created_by).name} for r in db.scalars(select(Record).where(Record.case_id==case.id).order_by(Record.created_at))]
        output['assessments']=[{'id':a.id,'facts':a.facts,'result':a.result,'created_at':a.created_at,'revision':a.case_revision} for a in assessments]
        output['decisions']=[{k:getattr(d,k) for k in ('id','number','sanction','basis','reason','official','date','created_at')} for d in db.scalars(select(Decision).where(Decision.case_id==case.id))]
        output['attachments']=[{'id':a.id,'name':a.name,'created_at':a.created_at} for a in db.scalars(select(Attachment).where(Attachment.case_id==case.id))]
    return output
