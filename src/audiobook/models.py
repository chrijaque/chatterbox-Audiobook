from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
import time

class AudioFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"

class VoiceProfile(BaseModel):
    """Voice profile configuration"""
    name: str = Field(..., description="Unique identifier for the voice")
    display_name: Optional[str] = Field(None, description="Display name for the voice")
    description: Optional[str] = Field(None, description="Description of the voice")
    audio_file: str = Field(..., description="Path to reference audio file")
    exaggeration: float = Field(0.5, description="Voice exaggeration level (0.0-1.0)")
    cfg_weight: float = Field(0.5, description="Classifier-free guidance weight (0.0-1.0)")
    temperature: float = Field(0.8, description="Generation temperature (0.0-1.0)")
    created_date: float = Field(default_factory=time.time, description="Profile creation timestamp")
    normalization_enabled: bool = Field(False, description="Whether audio normalization is enabled")
    target_level_db: float = Field(-18.0, description="Target audio level in dB")
    normalization_applied: bool = Field(False, description="Whether normalization was applied")
    original_level_info: Optional[Dict[str, float]] = Field(None, description="Original audio level information")
    version: str = Field("2.0", description="Profile version")

class TTSGenerationSettings(BaseModel):
    """Settings for TTS generation"""
    text: str = Field(..., description="Text to convert to speech")
    voice_name: str = Field(..., description="Name of the voice profile to use")
    chunk_size: int = Field(50, description="Maximum words per chunk")
    exaggeration: Optional[float] = Field(None, description="Override voice profile exaggeration")
    temperature: Optional[float] = Field(None, description="Override voice profile temperature")
    cfg_weight: Optional[float] = Field(None, description="Override voice profile CFG weight")

class AudioProcessingSettings(BaseModel):
    """Audio processing settings"""
    enable_normalization: bool = Field(True, description="Whether to normalize audio output")
    target_level_db: float = Field(-18.0, description="Target audio level in dB")
    crossfade_duration: float = Field(0.1, description="Crossfade duration between chunks in seconds")
    output_format: AudioFormat = Field(AudioFormat.WAV, description="Output audio format")

def create_default_audio_settings() -> AudioProcessingSettings:
    return AudioProcessingSettings(
        enable_normalization=True,
        target_level_db=-18.0,
        crossfade_duration=0.1,
        output_format=AudioFormat.WAV
    )

class ProjectMetadata(BaseModel):
    """Project metadata"""
    name: str = Field(..., description="Project name")
    text_content: str = Field(..., description="Original text content")
    voice_profile: VoiceProfile = Field(..., description="Voice profile used")
    chunks: List[str] = Field(default_factory=list, description="Text chunks")
    audio_files: List[str] = Field(default_factory=list, description="Generated audio file paths")
    created_date: float = Field(default_factory=time.time, description="Project creation timestamp")
    last_modified: float = Field(default_factory=time.time, description="Last modification timestamp")
    processing_settings: AudioProcessingSettings = Field(
        default_factory=create_default_audio_settings,
        description="Audio processing settings used"
    )
    generation_settings: TTSGenerationSettings = Field(..., description="TTS generation settings used")

class RunPodJobInput(BaseModel):
    """RunPod job input"""
    type: str = Field(..., description="Job type (tts or clone)")
    text: Optional[str] = Field(None, description="Text for TTS generation")
    voice_name: Optional[str] = Field(None, description="Voice name")
    reference_audio: Optional[str] = Field(None, description="Base64 encoded reference audio for cloning")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")

class RunPodJobOutput(BaseModel):
    """RunPod job output"""
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    content_type: Optional[str] = Field(None, description="Audio content type")
    success: bool = Field(..., description="Whether the job was successful")
    message: str = Field(..., description="Status or error message")
    error: Optional[str] = Field(None, description="Error message if job failed") 