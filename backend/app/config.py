from pathlib import Path
from typing import Literal
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./data/sipak.db'
    storage_path: Path = Path('data/documents')
    ollama_url: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'qwen2.5:3b-instruct-q4_K_M'
    ai_provider: Literal['openrouter','ollama'] = 'openrouter'
    ai_model: str = ''
    openrouter_api_key: SecretStr = SecretStr('')
    ai_timeout_seconds: int = 180
    max_upload_mb: int = 20
    session_hours: int = 8
    cookie_secure: bool = False
    bootstrap_email: str = ''
    bootstrap_password: str = ''
    bootstrap_name: str = 'Administrator'

settings = Settings()
