"""
RunPod-based TTS module for audiobook generation
"""
import runpod
import base64
import numpy as np
import torch
import librosa
import os
import json
from typing import Optional, Dict, Any, Tuple
from .config import settings
from pathlib import Path
from .config.paths import PathManager

# Initialize RunPod if configured
if settings.is_runpod_configured:
    runpod.api_key = settings.RUNPOD_API_KEY
    endpoint = runpod.Endpoint(settings.ENDPOINT_ID)

class AudiobookTTS:
    """Text-to-Speech engine for audiobook generation."""
    
    def __init__(self, use_runpod: bool = False):
        """Initialize the TTS engine.
        
        Args:
            use_runpod: Whether to use RunPod for inference
        """
        self.use_runpod = use_runpod
        self.path_manager = PathManager()
        self.sample_rate = 24000  # Standard sample rate for most TTS models
        
        if use_runpod:
            if not settings.is_runpod_configured:
                raise ValueError("RunPod API key not configured. Please set RUNPOD_API_KEY in settings.")
            self.endpoint = runpod.Endpoint(settings.ENDPOINT_ID)
    
    def generate_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        output_path: Optional[str] = None,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        **kwargs
    ) -> str:
        """Generate speech from text using specified voice.
        
        Args:
            text: Text to convert to speech
            voice_name: Name of voice to use (None for default)
            output_path: Path to save audio file (None for auto-generated)
            exaggeration: Voice exaggeration factor (0.25-2.0)
            temperature: Generation temperature (0.1-1.0)
            cfg_weight: CFG weight (0.2-1.0)
            **kwargs: Additional parameters
            
        Returns:
            Path to generated audio file
        """
        try:
            # Load voice configuration if specified
            voice_config = {}
            voice_id = None
            
            if voice_name:
                voice_path = self.path_manager.get_voice_clones_path() / voice_name
                config_path = voice_path / "config.json"
                if not config_path.exists():
                    raise FileNotFoundError(f"Voice not found: {voice_name}")
                
                with open(config_path, "r") as f:
                    voice_config = json.load(f)
                    voice_id = voice_config.get("voice_id")
                
                # If no voice ID, we need to clone the voice first
                if not voice_id:
                    voice_id = self._clone_voice(voice_path / "original.wav", exaggeration)
                    # Save the voice ID back to config
                    voice_config["voice_id"] = voice_id
                    with open(config_path, "w") as f:
                        json.dump(voice_config, f, indent=2)
            
            # Generate output path if not specified
            if not output_path:
                output_path = self.path_manager.get_voice_output_path() / f"{voice_name or 'default'}_output.wav"
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate speech
            if self.use_runpod:
                audio_data = self._generate_speech_runpod(
                    text=text,
                    voice_id=voice_id,
                    exaggeration=exaggeration,
                    temperature=temperature,
                    cfg_weight=cfg_weight,
                    **kwargs
                )
            else:
                audio_data = self._generate_speech_local(
                    text=text,
                    voice_path=voice_path if voice_name else None,
                    exaggeration=exaggeration,
                    temperature=temperature,
                    cfg_weight=cfg_weight,
                    **kwargs
                )
            
            # Save audio to file
            import soundfile as sf
            sf.write(output_path, audio_data, self.sample_rate)
            
            return str(output_path)
            
        except Exception as e:
            import traceback
            print(f"Error generating speech: {traceback.format_exc()}")
            raise
    
    def _clone_voice(self, voice_path: Path, exaggeration: float = 0.5) -> str:
        """Clone a voice from an audio file.
        
        Args:
            voice_path: Path to voice audio file
            exaggeration: Voice exaggeration factor
            
        Returns:
            Voice ID for the cloned voice
        """
        try:
            print(f"Cloning voice from: {voice_path}")
            
            # Load and encode the audio file
            audio, _ = librosa.load(str(voice_path), sr=self.sample_rate)
            audio_bytes = audio.tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode()
            
            if self.use_runpod:
                # Call RunPod endpoint for voice cloning
                response = self.endpoint.run({
                    "type": "clone",
                    "reference_audio": audio_b64,
                    "voice_name": voice_path.parent.name,
                    "parameters": {
                        "exaggeration": exaggeration
                    }
                })
                
                if response.get("error"):
                    raise ValueError(f"RunPod error: {response['error']}")
                
                voice_id = response.get("voice_id")
                if not voice_id:
                    raise ValueError("No voice ID returned from RunPod")
                
                return voice_id
            else:
                # TODO: Implement local voice cloning
                print("Warning: Local voice cloning not implemented, using dummy voice ID")
                return "dummy_voice_id"
                
        except Exception as e:
            print(f"Error cloning voice: {e}")
            raise
    
    def _generate_speech_runpod(
        self,
        text: str,
        voice_id: Optional[str],
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        **kwargs
    ) -> np.ndarray:
        """Generate speech using RunPod."""
        try:
            # Call RunPod endpoint for generation
            response = self.endpoint.run({
                "type": "tts",
                "text": text,
                "voice_id": voice_id,
                "parameters": {
                    "exaggeration": exaggeration,
                    "temperature": temperature,
                    "cfg_weight": cfg_weight,
                    **kwargs
                }
            })
            
            if response.get("error"):
                raise ValueError(f"RunPod error: {response['error']}")
            
            # Convert base64 audio to numpy array
            audio_data = base64.b64decode(response["audio_data"])
            return np.frombuffer(audio_data, dtype=np.float32)
            
        except Exception as e:
            print(f"Error generating speech with RunPod: {e}")
            raise
    
    def _generate_speech_local(
        self,
        text: str,
        voice_path: Optional[Path],
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        **kwargs
    ) -> np.ndarray:
        """Generate speech locally."""
        # TODO: Implement local TTS generation
        print("Warning: Local TTS generation not implemented, generating dummy audio")
        
        # Generate 1 second of silence as dummy audio
        return np.zeros(self.sample_rate, dtype=np.float32)
    
    def get_voice_path(self, voice_name: str) -> Optional[Path]:
        """Get the path to a voice clone directory."""
        voice_path = self.path_manager.get_voice_clones_path() / voice_name
        if voice_path.exists() and voice_path.is_dir():
            return voice_path
        return None 