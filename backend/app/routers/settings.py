import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.services.gemini_service import gemini_service

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

class APIKeyPayload(BaseModel):
    api_key: str

@router.get("")
def get_system_settings():
    """Returns status of system integrations and API keys."""
    has_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
    return {
        "gemini_api_key_configured": has_key,
        "gemini_model": settings.GEMINI_MODEL,
        "database": "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql",
        "smtp_host": settings.SMTP_HOST
    }

@router.post("/key")
def update_gemini_api_key(payload: APIKeyPayload):
    """Updates the Gemini API key, persists to .env, and initializes GenAI client."""
    key = payload.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    # Update runtime settings
    settings.GEMINI_API_KEY = key
    os.environ["GEMINI_API_KEY"] = key

    # Write to .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"GEMINI_API_KEY={key}\n")
        f.write(f"GEMINI_MODEL={settings.GEMINI_MODEL}\n")
        f.write(f"DATABASE_URL={settings.DATABASE_URL}\n")
        f.write(f"SMTP_HOST={settings.SMTP_HOST}\n")
        f.write(f"SMTP_PORT={settings.SMTP_PORT}\n")

    # Re-initialize Gemini client
    gemini_service.set_api_key(key)

    return {"status": "success", "message": "Gemini API key configured successfully"}

@router.post("/test")
async def test_gemini_connection():
    """Tests the configured Gemini API key with a fast ping."""
    if not gemini_service.client:
        return {"success": False, "error": "Gemini client is not initialized. Please provide a valid Gemini API key first."}
    try:
        response = gemini_service.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="Hello! Confirm connection in 3 words."
        )
        return {
            "success": True,
            "model": settings.GEMINI_MODEL,
            "reply": response.text.strip() if response and response.text else "Connected"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
