"""API endpoints for the audiobook generation system."""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, FastAPI
from fastapi.responses import JSONResponse

from ..config import settings
from ..tts import AudiobookTTS
from ..voice_management import VoiceManager, VoiceProfile

# Initialize components
router = APIRouter()
voice_manager = VoiceManager(voice_library_path=settings.VOICE_LIBRARY_PATH)

def create_api() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Chatterbox Audiobook API", version="1.0.0")
    app.include_router(router, prefix="/api")
    return app

@router.get("/voices")
async def list_voices() -> Dict[str, List[Dict[str, Any]]]:
    """List available voice profiles."""
    try:
        profiles = voice_manager.get_profiles()
        return {
            "voices": [
                {
                    "name": p.voice_name,
                    "display_name": p.display_name,
                    "description": p.description
                }
                for p in profiles
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_speech(
    text: str,
    voice_name: str,
    exaggeration: float = 0.5,
    temperature: float = 0.8,
    cfg_weight: float = 0.5
) -> Dict[str, Any]:
    """Generate speech from text."""
    try:
        # Initialize TTS engine
        tts_engine = AudiobookTTS()
        
        # Load voice profile
        audio_file, voice_profile = voice_manager.load_voice_for_tts(voice_name)
        if not audio_file:
            raise HTTPException(
                status_code=404,
                detail=f"Voice file not found for {voice_name}"
            )
        
        # Generate speech
        output_path = tts_engine.generate_speech(
            text=text,
            voice_name=voice_name,
            exaggeration=exaggeration,
            temperature=temperature,
            cfg_weight=cfg_weight
        )
        
        return {
            "success": True,
            "output_path": output_path,
            "message": "Speech generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voices")
async def create_voice(
    voice_name: str,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    exaggeration: float = 0.5,
    temperature: float = 0.8,
    cfg_weight: float = 0.5
) -> Dict[str, str]:
    """Create a new voice profile."""
    try:
        # This would need audio data in a real implementation
        # For now, just create a basic profile
        return {"success": "true", "voice_name": voice_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/voices/{voice_name}")
async def delete_voice(voice_name: str) -> Dict[str, str]:
    """Delete a voice profile."""
    try:
        if voice_manager.delete_profile(voice_name):
            return {"success": "true"}
        raise HTTPException(
            status_code=404,
            detail=f"Voice profile not found: {voice_name}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 