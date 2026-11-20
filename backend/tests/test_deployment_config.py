import pytest
from backend.app.config import Settings


@pytest.mark.parametrize('url,expected',[
    ('postgres://synthetic:p%40ss@db.internal:5432/sipak?sslmode=require','postgresql+psycopg://synthetic:p%40ss@db.internal:5432/sipak?sslmode=require'),
    ('postgresql://synthetic:pass@db.internal:5432/sipak','postgresql+psycopg://synthetic:pass@db.internal:5432/sipak'),
    ('postgresql+psycopg://synthetic:pass@db.internal/sipak','postgresql+psycopg://synthetic:pass@db.internal/sipak'),
    ('sqlite:///./data/sipak.db','sqlite:///./data/sipak.db'),
])
def test_hosting_database_url_uses_installed_driver(url,expected):
    assert Settings(_env_file=None,database_url=url).database_url==expected
