"""
Text-to-Speech module for the audiobook system.
"""
from .engine import TTSEngine
from .text_processor import TextProcessor, TextChunk
from .audio_processor import AudioProcessor

import runpod
import base64
import json
import os
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from ..config import settings
from ..config.paths import PathManager

__all__ = [
    'TTSEngine',
    'TextProcessor',
    'TextChunk',
    'AudioProcessor',
    'AudiobookTTS'
]

class AudiobookTTS:
    """TTS engine for audiobook generation."""
    
    def __init__(self):
        if settings.is_runpod_configured:
            runpod.api_key = settings.RUNPOD_API_KEY
            self.endpoint_id = settings.RUNPOD_ENDPOINT_ID
            self.use_runpod = True
        else:
            self.use_runpod = False
        self.path_manager = PathManager()

    def save_voice_sample(
        self,
        audio_data: bytes,
        voice_name: str,
        description: Optional[str] = None
    ) -> str:
        """Save a voice sample recording.
        
        Args:
            audio_data: Raw audio data in WAV format
            voice_name: Name for the voice sample
            description: Optional description of the voice
            
        Returns:
            str: Name of the saved voice sample
        """
        # Sanitize voice name
        safe_name = self._sanitize_name(voice_name)
        if not safe_name:
            raise ValueError("Invalid voice name")
            
        # Create voice sample directory
        voice_dir = self.path_manager.get_voice_samples_path() / safe_name
        voice_dir.mkdir(parents=True, exist_ok=True)
        
        # Save sample audio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = voice_dir / f"sample_{timestamp}.wav"
        with open(audio_path, "wb") as f:
            f.write(audio_data)
            
        # Create metadata
        metadata = {
            "display_name": voice_name,
            "description": description or "",
            "created_date": str(datetime.now().timestamp()),
            "samples": [audio_path.name]
        }
        
        metadata_path = voice_dir / "metadata.json"
        if metadata_path.exists():
            # Update existing metadata
            with open(metadata_path, "r") as f:
                existing = json.load(f)
                existing["samples"].append(audio_path.name)
                metadata["samples"] = existing["samples"]
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        return safe_name

    def clone_voice(
        self,
        audio_data: bytes,
        voice_name: str,
        description: Optional[str] = None
    ) -> str:
        """Clone a voice from audio data.
        
        Args:
            audio_data: Raw audio data in WAV format
            voice_name: Name for the cloned voice
            description: Optional description of the voice
            
        Returns:
            str: Name of the created voice
        """
        # Sanitize voice name
        safe_name = self._sanitize_name(voice_name)
        if not safe_name:
            raise ValueError("Invalid voice name")
            
        # Create voice clone directory
        voice_dir = self.path_manager.get_voice_clones_path() / safe_name
        voice_dir.mkdir(parents=True, exist_ok=True)
        
        # Save reference audio
        audio_path = voice_dir / "reference.wav"
        with open(audio_path, "wb") as f:
            f.write(audio_data)
            
        # Create config
        config = {
            "display_name": voice_name,
            "description": description or "",
            "reference_audio": "reference.wav",
            "exaggeration": 0.5,
            "cfg_weight": 0.5,
            "temperature": 0.8,
            "created_date": str(datetime.now().timestamp()),
            "min_p": 0.05,
            "top_p": 1.0,
            "repetition_penalty": 1.2,
            "version": "2.1"
        }
        
        config_path = voice_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        return safe_name

    def generate_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        min_p: float = 0.05,
        top_p: float = 1.0,
        repetition_penalty: float = 1.2
    ) -> bytes:
        """Generate speech using RunPod."""
        if not self.use_runpod:
            raise RuntimeError("RunPod is not configured")
            
        endpoint = runpod.Endpoint(self.endpoint_id)
        
        # If using a voice, load its config
        voice_config = {}
        if voice_name:
            config_path = self.path_manager.get_voice_clones_path() / voice_name / "config.json"
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        voice_config = json.load(f)
                except Exception as e:
                    print(f"Error loading voice config: {e}")
        
        # Merge voice config with provided parameters
        params = {
            "text": text,
            "voice_name": voice_name,
            **{k: voice_config.get(k, v) for k, v in {
                "exaggeration": exaggeration,
                "temperature": temperature,
                "cfg_weight": cfg_weight,
                "min_p": min_p,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty
            }.items()}
        }
        
        response = endpoint.run(params)
        
        if response.get("error"):
            raise RuntimeError(f"RunPod error: {response['error']}")
            
        audio_data = base64.b64decode(response["audio"])
        
        # Save the output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{voice_name or 'default'}_{timestamp}"
        output_dir = self.path_manager.get_tts_output_path() / self._sanitize_name(output_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save audio and metadata
        audio_path = output_dir / "audio.wav"
        with open(audio_path, "wb") as f:
            f.write(audio_data)
            
        metadata = {
            "text": text,
            "voice_name": voice_name,
            "created_date": str(datetime.now().timestamp()),
            "parameters": {
                "exaggeration": exaggeration,
                "temperature": temperature,
                "cfg_weight": cfg_weight,
                "min_p": min_p,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty
            }
        }
        
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
        return audio_data

    def list_voice_samples(self) -> List[Dict[str, Any]]:
        """List all available voice samples.
        
        Returns:
            List[dict]: List of voice sample information
        """
        samples = []
        
        try:
            for voice_dir in self.path_manager.get_voice_samples_path().iterdir():
                if not voice_dir.is_dir():
                    continue
                    
                metadata_path = voice_dir / "metadata.json"
                if not metadata_path.exists():
                    continue
                    
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    samples.append({
                        "name": voice_dir.name,
                        "display_name": metadata.get("display_name", voice_dir.name),
                        "description": metadata.get("description", ""),
                        "created_date": metadata.get("created_date"),
                        "sample_count": len(metadata.get("samples", []))
                    })
                except Exception as e:
                    print(f"Error loading voice sample {voice_dir.name}: {e}")
                    
        except Exception as e:
            print(f"Error listing voice samples: {e}")
            
        return samples

    def list_voice_clones(self) -> List[Dict[str, Any]]:
        """List all available voice clones.
        
        Returns:
            List[dict]: List of voice clone information
        """
        clones = []
        
        try:
            for voice_dir in self.path_manager.get_voice_clones_path().iterdir():
                if not voice_dir.is_dir():
                    continue
                    
                config_path = voice_dir / "config.json"
                if not config_path.exists():
                    continue
                    
                try:
                    with open(config_path, "r") as f:
                        config = json.load(f)
                    clones.append({
                        "name": voice_dir.name,
                        "display_name": config.get("display_name", voice_dir.name),
                        "description": config.get("description", ""),
                        "created_date": config.get("created_date")
                    })
                except Exception as e:
                    print(f"Error loading voice clone {voice_dir.name}: {e}")
                    
        except Exception as e:
            print(f"Error listing voice clones: {e}")
            
        return clones

    def delete_voice_sample(self, voice_name: str) -> bool:
        """Delete a voice sample.
        
        Args:
            voice_name: Name of the voice sample to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        voice_dir = self.path_manager.get_voice_samples_path() / voice_name
        if not voice_dir.exists():
            return False
            
        try:
            shutil.rmtree(voice_dir)
            return True
        except Exception as e:
            print(f"Error deleting voice sample {voice_name}: {e}")
            return False

    def delete_voice_clone(self, voice_name: str) -> bool:
        """Delete a voice clone.
        
        Args:
            voice_name: Name of the voice clone to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        voice_dir = self.path_manager.get_voice_clones_path() / voice_name
        if not voice_dir.exists():
            return False
            
        try:
            shutil.rmtree(voice_dir)
            return True
        except Exception as e:
            print(f"Error deleting voice clone {voice_name}: {e}")
            return False

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize a name for use in filenames."""
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        return safe_name.replace(' ', '_') 