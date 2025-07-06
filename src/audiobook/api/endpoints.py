"""API endpoints for voice cloning and TTS."""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
from ..tts.engine import TTSEngine
from ..config import settings
from .runpod_client import RunPodClient
from ..tts.text_processor import validate_text_input
from ..voice_management import VoiceManager
from ..tts.audio_processor import AudioProcessor
import os
import tempfile
import uuid

from ..tts import AudiobookTTS
from ..models import (
    VoiceProfile,
    TTSGenerationSettings,
    AudioProcessingSettings,
    ProjectMetadata,
    AudioFormat
)

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
    text: str = Field(..., description="Text to convert to speech")
    voice_name: str = Field(..., description="Name of the voice profile to use")
    chunk_size: int = Field(default=50, description="Maximum words per chunk")
    enable_normalization: bool = Field(default=True, description="Whether to normalize audio output")
    target_level_db: float = Field(default=-18.0, description="Target audio level in dB")

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
    
    @app.post("/tts/generate")
    async def generate_tts(
        generation_settings: TTSGenerationSettings,
        processing_settings: AudioProcessingSettings = AudioProcessingSettings(),
        background_tasks: BackgroundTasks = None
    ):
        """Generate TTS audio from text using specified voice profile"""
        # Validate text input
        is_valid, message = validate_text_input(generation_settings.text)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Load voice profile
        profile = voice_manager.get_voice_profile(generation_settings.voice_name)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Voice profile '{generation_settings.voice_name}' not found")
        
        try:
            # Generate audio chunks
            audio_chunks = tts_engine.generate_tts(
                generation_settings.text,
                profile.audio_file,
                chunk_size=generation_settings.chunk_size,
                exaggeration=generation_settings.exaggeration or profile.exaggeration,
                temperature=generation_settings.temperature or profile.temperature,
                cfg_weight=generation_settings.cfg_weight or profile.cfg_weight
            )
            
            # Process audio
            if processing_settings.enable_normalization:
                audio_chunks = [
                    audio_processor.normalize_audio(chunk, processing_settings.target_level_db)
                    for chunk in audio_chunks
                ]
            
            # Combine chunks with crossfade
            final_audio = audio_processor.combine_audio_chunks(
                audio_chunks,
                crossfade_duration=processing_settings.crossfade_duration
            )
            
            # Save to temporary file
            temp_dir = tempfile.mkdtemp()
            output_file = os.path.join(temp_dir, f"{uuid.uuid4()}.{processing_settings.output_format}")
            
            # Save combined audio
            audio_processor.save_audio_chunks([final_audio], "temp", temp_dir)
            
            # Schedule cleanup
            if background_tasks:
                background_tasks.add_task(lambda: os.remove(output_file) if os.path.exists(output_file) else None)
                background_tasks.add_task(lambda: os.rmdir(temp_dir) if os.path.exists(temp_dir) else None)
            
            return FileResponse(
                output_file,
                media_type=f"audio/{processing_settings.output_format}",
                filename=f"generated_audio.{processing_settings.output_format}"
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/voice/create")
    async def create_voice_profile(
        profile: VoiceProfile,
        audio_file: UploadFile = File(...),
    ):
        """Create a new voice profile"""
        # Save uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file.close()
            
            # Validate audio sample
            is_valid, message = voice_manager.validate_voice_sample(temp_file.name)
            if not is_valid:
                raise HTTPException(status_code=400, detail=message)
            
            # Save voice profile
            result = voice_manager.save_voice_profile(
                profile.name,
                profile.display_name,
                profile.description,
                temp_file.name,
                profile.exaggeration,
                profile.cfg_weight,
                profile.temperature,
                profile.normalization_enabled,
                profile.target_level_db
            )
            
            return {"message": result}
            
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    @app.delete("/voice/{voice_name}")
    async def delete_voice_profile(voice_name: str):
        """Delete a voice profile"""
        message, profiles = voice_manager.delete_voice_profile(voice_name)
        if "Error" in message or "not found" in message:
            raise HTTPException(status_code=404, detail=message)
        return {"message": message}
    
    @app.get("/voice/list")
    async def list_voice_profiles() -> List[VoiceProfile]:
        """List all available voice profiles"""
        return voice_manager.get_voice_profiles()
    
    @app.get("/voice/{voice_name}")
    async def get_voice_profile(voice_name: str) -> VoiceProfile:
        """Get details of a specific voice profile"""
        profile = voice_manager.get_voice_profile(voice_name)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Voice profile '{voice_name}' not found")
        return profile
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}
    
    return app 

async def get_runpod_client():
    """Dependency to get RunPod client instance"""
    return RunPodClient() 