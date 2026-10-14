from pydantic_settings import BaseSettings
from typing import Optional
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IS_VERCEL = bool(os.getenv("VERCEL"))
if IS_VERCEL:
    DEFAULT_STORAGE_DIR = "/tmp/storage"
    DEFAULT_DB_FILE = "/tmp/meetings.db"
else:
    DEFAULT_STORAGE_DIR = os.path.join(BASE_DIR, "storage")
    DEFAULT_DB_FILE = os.path.join(BASE_DIR, "meetings.db").replace("\\", "/")


class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE}")

    STORAGE_DIR: str = os.getenv("STORAGE_DIR", DEFAULT_STORAGE_DIR)
    RAW_AUDIO_SUBDIR: str = "audio_raw"
    PDF_SUBDIR: str = "pdf_reports"

    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "1025"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", None)
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "meetings@ai-agent.local")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "AI Meeting Assistant")

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    AUTO_DISPATCH_EMAILS: bool = os.getenv("AUTO_DISPATCH_EMAILS", "true").lower() == "true"

    class Config:
        env_file = os.path.join(BASE_DIR, ".env")
        extra = "ignore"

settings = Settings()

# Ensure storage directories exist
try:
    os.makedirs(os.path.join(settings.STORAGE_DIR, settings.RAW_AUDIO_SUBDIR), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, settings.PDF_SUBDIR), exist_ok=True)
except Exception:
    pass

