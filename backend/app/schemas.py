from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, SecretStr
from datetime import date

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Citation(Strict):
    page: int = Field(ge=1)
    quote: str = Field(min_length=1)

class Sourced(Strict):
    sources: list[Citation] = Field(default_factory=list)

class CaseInformation(Sourced):
    bap_number: str | None = None
    examination_date: str | None = None
    case_type: str | None = None
    alleged_category: str | None = None
    incident_date: str | None = None
    incident_time: str | None = None
    incident_location: str | None = None
    case_summary: str | None = None

class Person(Sourced):
    name: str | None = None
    identity_number: str | None = None
    praja_level: str | None = None
    age: int | None = None
    gender: str | None = None
    address: str | None = None
    campus: str | None = None
    role: Literal['Terperiksa','Terlapor','Terduga Pelaku','Korban','Saksi','Pelapor','Pengasuh','Pemeriksa','Pihak Lainnya'] | None = None
    description: str | None = None

class Evidence(Sourced):
    name: str | None = None
    type: str | None = None
    description: str | None = None
    related_person: str | None = None
    relationship: str | None = None

class Witness(Sourced):
    name: str | None = None
    relationship: str | None = None
    statement: str | None = None

class Event(Sourced):
    date: str | None = None
    time: str | None = None
    location: str | None = None
    description: str | None = None
    persons: list[str] = Field(default_factory=list)

class Relationship(Sourced):
    subject: str | None = None
    relation: str | None = None
    object: str | None = None

class LegalProvision(Sourced):
    reference: str | None = None
    text: str | None = None

class Extraction(Strict):
    case_information: CaseInformation = Field(default_factory=CaseInformation)
    involved_persons: list[Person] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    witnesses: list[Witness] = Field(default_factory=list)
    chronology: list[Event] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    legal_provisions_mentioned: list[LegalProvision] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)

class Login(Strict):
    email: str = Field(max_length=200, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(max_length=256)

class AIConfigUpdate(Strict):
    provider: Literal['openrouter','ollama']
    model: str = Field(min_length=1,max_length=200,pattern=r'^[A-Za-z0-9._:/-]+$')
    api_key: SecretStr | None = None
    clear_api_key: bool = False

class InferenceConsent(Strict):
    cloud_consent: bool = False
    expected_provider: str = ''
    expected_model: str = ''

class UserCreate(Login):
    name: str = Field(min_length=2,max_length=200)
    role: Literal['admin','investigator','reviewer','decision_maker','viewer']

class Review(Strict):
    extraction: Extraction
    note: str = Field(min_length=5,max_length=10000)
    approve: bool = False
    expected_revision: int

class Condition(Strict):
    field: str = Field(pattern=r'^[a-z_]{2,60}$')
    equals: str | int | bool

class RuleCreate(Strict):
    article_id: str
    paragraph: str = Field(min_length=1,max_length=30)
    letter: str = Field(max_length=30)
    text: str = Field(min_length=10)
    category: Literal['Ringan','Sedang','Berat']
    sanction: str = Field(min_length=3)
    sanction_basis: str = Field(min_length=10)
    sanction_article_id: str
    conditions: list[Condition] = Field(min_length=2)

class Fact(Strict):
    value: str | int | bool
    sources: list[Citation] = Field(min_length=1)

class AnalysisInput(Strict):
    facts: dict[str, Fact]
    note: str = Field(min_length=5)

class Note(Strict):
    kind: Literal['note','classification_accepted','classification_rejected','commission_recommendation'] = 'note'
    text: str = Field(min_length=5,max_length=20000)

class WorkflowUpdate(Strict):
    stage: int = Field(ge=0,le=11)
    date: str = Field(min_length=10,max_length=30)
    responsible: str = Field(min_length=3,max_length=200)
    note: str = Field(min_length=5,max_length=10000)
    attachment_ids: list[str] = Field(min_length=1)

    @field_validator('date')
    @classmethod
    def valid_date(cls,value):
        date.fromisoformat(value)
        return value

class DecisionCreate(Strict):
    number: str = Field(min_length=3,max_length=200)
    sanction: str = Field(min_length=3,max_length=2000)
    basis: str = Field(min_length=10,max_length=10000)
    reason: str = Field(min_length=10,max_length=10000)
    official: str = Field(min_length=3,max_length=200)
    date: str = Field(min_length=10,max_length=30)

    @field_validator('date')
    @classmethod
    def valid_date(cls,value):
        date.fromisoformat(value)
        return value

WORKFLOW = ['Pelaporan Dugaan Pelanggaran Berat','Pendalaman Awal','Pelaporan kepada Rektor','Penugasan Tim Pemeriksa','Pemeriksaan Praja','Penyusunan BAP dan Laporan Hasil Pemeriksaan','Penyampaian Hasil Pemeriksaan','Rapat Komisi Disiplin Praja','Rekomendasi Komisi Disiplin Praja','Rapat Pimpinan dan/atau Komisi Senat','Penetapan Keputusan Rektor','Penyampaian Keputusan']
