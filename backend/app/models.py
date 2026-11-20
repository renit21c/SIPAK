import uuid
from sqlalchemy import String, Text, ForeignKey, JSON, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, now

def uid(): return str(uuid.uuid4())

class ApplicationSetting(Base):
    __tablename__ = 'application_settings'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)

class Role(Base):
    __tablename__ = 'roles'
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    permissions: Mapped[list] = mapped_column(JSON)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(ForeignKey('roles.name'))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Session(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[str] = mapped_column(String(50))

class Document(Base):
    __tablename__ = 'bap_documents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default='Menunggu')
    stage: Mapped[int] = mapped_column(Integer, default=1)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

class DocumentPage(Base):
    __tablename__ = 'document_pages'
    __table_args__ = (UniqueConstraint('document_id', 'number'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('bap_documents.id'))
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

class Case(Base):
    __tablename__ = 'cases'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    number: Mapped[str] = mapped_column(String(100), unique=True)
    document_id: Mapped[str] = mapped_column(ForeignKey('bap_documents.id'), unique=True)
    status: Mapped[str] = mapped_column(String(80), default='Analisis Awal AI')
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(50), default=now)

class Entity(Base):
    __tablename__ = 'extracted_entities'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'))
    kind: Mapped[str] = mapped_column(String(60))
    value: Mapped[dict] = mapped_column(JSON)

class Source(Base):
    __tablename__ = 'extraction_sources'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    entity_id: Mapped[str] = mapped_column(ForeignKey('extracted_entities.id', ondelete='CASCADE'))
    page: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text)

class Regulation(Base):
    __tablename__ = 'regulations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(Text)
    number: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(100))
    effective_date: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

class Article(Base):
    __tablename__ = 'regulatory_articles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    regulation_id: Mapped[str] = mapped_column(ForeignKey('regulations.id'))
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

class Provision(Base):
    __tablename__ = 'regulatory_provisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    article_id: Mapped[str] = mapped_column(ForeignKey('regulatory_articles.id'))
    paragraph: Mapped[str] = mapped_column(String(30))
    letter: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20))
    sanction: Mapped[str] = mapped_column(Text)
    sanction_basis: Mapped[str] = mapped_column(Text)
    conditions: Mapped[list] = mapped_column(JSON)
    related_articles: Mapped[list] = mapped_column(JSON, default=list)

class Assessment(Base):
    __tablename__ = 'violation_assessments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'))
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    facts: Mapped[dict] = mapped_column(JSON)
    result: Mapped[list] = mapped_column(JSON)
    case_revision: Mapped[int] = mapped_column(Integer)

class Record(Base):
    __tablename__ = 'examination_records'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'))
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(50), default=now)

class Decision(Base):
    __tablename__ = 'official_decisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'))
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    number: Mapped[str] = mapped_column(String(200), unique=True)
    sanction: Mapped[str] = mapped_column(Text)
    basis: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    official: Mapped[str] = mapped_column(String(200))
    date: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(50), default=now)

class Attachment(Base):
    __tablename__ = 'supporting_documents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'))
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[str] = mapped_column(String(50), default=now)

class Audit(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(50), default=now)
