"""API endpoints for voice cloning and TTS."""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
from ..tts.engine import TTSEngine
from ..config import settings
from .runpod_client import RunPodClient

from ..tts import AudiobookTTS

# API Models
class VoiceProfile(BaseModel):
    """Voice profile creation request."""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    exaggeration: float = 0.5
    cfg_weight: float = 0.5
    temperature: float = 0.8

class TTSRequest(BaseModel):
    """Text-to-speech generation request."""
    text: str
    voice_name: Optional[str] = None
    exaggeration: Optional[float] = 0.5
    temperature: Optional[float] = 0.8
    cfg_weight: Optional[float] = 0.5
    min_p: Optional[float] = 0.05
    top_p: Optional[float] = 1.0
    repetition_penalty: Optional[float] = 1.2

class ChunkingRequest(BaseModel):
    """Text chunking request."""
    text: str
    max_words: int = 50

class VoiceCloneRequest(BaseModel):
    """Request model for voice cloning."""
    voice_name: str
    description: Optional[str] = None

class Voice(BaseModel):
    """Voice model."""
    name: str
    description: Optional[str] = None

# API Setup
def create_api(tts_engine: TTSEngine) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="Chatterbox TTS API")
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Welcome to Chatterbox TTS API"}
    
    @app.post("/api/v1/voices/create")
    async def create_voice(
        profile: VoiceProfile,
        audio_file: UploadFile = File(...)
    ) -> Dict[str, Any]:
        """Create a new voice profile."""
        try:
            # Save uploaded audio file
            audio_data = await audio_file.read()
            temp_path = settings.save_temp_audio(audio_data)
            
            # Create voice profile
            settings.save_voice_profile(
                name=profile.name,
                display_name=profile.display_name or profile.name,
                description=profile.description,
                audio_file=temp_path,
                exaggeration=profile.exaggeration,
                cfg_weight=profile.cfg_weight,
                temperature=profile.temperature
            )
            
            return {
                "status": "success",
                "message": "Voice profile created successfully",
                "voice": profile.dict()
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/v1/voices/list")
    async def list_voices() -> Dict[str, List[Dict[str, Any]]]:
        """List all available voice profiles."""
        try:
            voices = settings.get_voice_profiles()
            return {
                "status": "success",
                "voices": voices
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/voices/{voice_name}")
    async def delete_voice(voice_name: str) -> Dict[str, str]:
        """Delete a voice profile."""
        try:
            settings.delete_voice_profile(voice_name)
            return {
                "status": "success",
                "message": f"Voice profile '{voice_name}' deleted successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @app.post("/tts")
    async def generate_speech(request: TTSRequest):
        """Generate speech from text."""
        try:
            audio_data = tts_engine.generate_speech(
                text=request.text,
                voice_name=request.voice_name,
                exaggeration=request.exaggeration,
                temperature=request.temperature,
                cfg_weight=request.cfg_weight,
                min_p=request.min_p,
                top_p=request.top_p,
                repetition_penalty=request.repetition_penalty
            )
            return Response(
                content=audio_data,
                media_type="audio/wav"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @app.post("/voices")
    async def clone_voice(
        request: VoiceCloneRequest,
        audio_file: UploadFile = File(...)
    ):
        """Clone a voice from audio file."""
        try:
            audio_data = await audio_file.read()
            voice_name = tts_engine.clone_voice(
                audio_data=audio_data,
                voice_name=request.voice_name,
                description=request.description
            )
            return JSONResponse(
                content={"voice_name": voice_name},
                status_code=201
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @app.get("/voices")
    async def list_voices() -> List[Voice]:
        """List all available voices."""
        try:
            voices = tts_engine.list_voices()
            return [Voice(**voice) for voice in voices]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}
    
    return app 

async def get_runpod_client():
    """Dependency to get RunPod client instance"""
    return RunPodClient() 