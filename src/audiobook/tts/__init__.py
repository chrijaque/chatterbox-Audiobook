"""
Text-to-Speech module for the audiobook system.
"""
from .engine import TTSEngine
from .text_processor import TextProcessor, TextChunk
from .audio_processor import AudioProcessor

import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, NamedTuple
from ..config import settings
from ..config.paths import PathManager
from ..voice_management import VoiceManager

__all__ = [
    'TTSEngine',
    'TextProcessor',
    'TextChunk',
    'AudioProcessor',
    'AudiobookTTS'
]

class VoiceProfile(NamedTuple):
    """Voice profile information."""
    name: str
    description: str
    created_date: str

class AudiobookTTS:
    """TTS engine for audiobook generation."""
    
    def __init__(self, use_runpod: bool = False):
        """Initialize TTS engine.
        
        Args:
            use_runpod: Whether to use RunPod for voice cloning
        """
        self.use_runpod = use_runpod and settings.is_runpod_configured
        if use_runpod and not settings.is_runpod_configured:
            print("Warning: RunPod requested but not configured. Voice cloning will be disabled.")
            
        self.path_manager = PathManager()
        self.voice_manager = VoiceManager(voice_library_path=settings.VOICE_LIBRARY_PATH)
        self.audio_processor = AudioProcessor()
        self.text_processor = TextProcessor()
        self.tts_engine = TTSEngine()

    def save_voice_sample(
        self,
        audio_path: str,
        name: str,
        description: Optional[str] = None
    ) -> str:
        """Save a voice sample recording.
        
        Args:
            audio_path: Path to the audio file
            name: Name for the voice sample
            description: Optional description of the voice
            
        Returns:
            str: Name of the saved voice sample
        """
        # Sanitize voice name
        safe_name = self._sanitize_name(name)
        if not safe_name:
            raise ValueError("Invalid voice name")
            
        # Create voice sample directory
        voice_dir = self.path_manager.get_voice_samples_path() / safe_name
        voice_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy sample audio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = voice_dir / f"sample_{timestamp}.wav"
        shutil.copy2(audio_path, dest_path)
            
        # Create metadata
        metadata = {
            "display_name": name,
            "description": description or "",
            "created_date": str(datetime.now().timestamp()),
            "samples": [dest_path.name]
        }
        
        metadata_path = voice_dir / "metadata.json"
        if metadata_path.exists():
            # Update existing metadata
            with open(metadata_path, "r") as f:
                existing = json.load(f)
                existing["samples"].append(dest_path.name)
                metadata["samples"] = existing["samples"]
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        return safe_name

    def list_voice_profiles(self) -> List[VoiceProfile]:
        """List all available voice profiles (samples and clones).
        
        Returns:
            List[VoiceProfile]: List of voice profiles
        """
        profiles = []
        
        # List voice samples
        samples_dir = self.path_manager.get_voice_samples_path()
        if samples_dir.exists():
            for voice_dir in samples_dir.iterdir():
                if voice_dir.is_dir():
                    metadata_path = voice_dir / "metadata.json"
                    try:
                        if metadata_path.exists():
                            with open(metadata_path, "r") as f:
                                metadata = json.load(f)
                        else:
                            # Create default metadata for existing samples
                            metadata = {
                                "display_name": voice_dir.name,
                                "description": "",
                                "created_date": str(voice_dir.stat().st_ctime),
                                "samples": [f.name for f in voice_dir.glob("*.wav")]
                            }
                            with open(metadata_path, "w") as f:
                                json.dump(metadata, f, indent=2)
                        
                        profiles.append(VoiceProfile(
                            name=voice_dir.name,
                            description=metadata.get("description", ""),
                            created_date=metadata.get("created_date", "")
                        ))
                    except Exception as e:
                        print(f"Warning: Error handling metadata for {voice_dir}: {e}")
                        continue
        
        # List voice clones
        clones_dir = self.path_manager.get_voice_clones_path()
        if clones_dir.exists():
            for voice_dir in clones_dir.iterdir():
                if voice_dir.is_dir():
                    config_path = voice_dir / "config.json"
                    if config_path.exists():
                        try:
                            with open(config_path, "r") as f:
                                config = json.load(f)
                                profiles.append(VoiceProfile(
                                    name=voice_dir.name,
                                    description=config.get("description", ""),
                                    created_date=config.get("created_date", "")
                                ))
                        except Exception as e:
                            print(f"Error loading config for {voice_dir}: {e}")
        
        return sorted(profiles, key=lambda p: p.created_date, reverse=True)

    def delete_voice_profile(self, voice_name: str) -> str:
        """Delete a voice profile (sample or clone).
        
        Args:
            voice_name: Name of the voice to delete
            
        Returns:
            str: Success message
        """
        # Check samples directory
        sample_dir = self.path_manager.get_voice_samples_path() / voice_name
        if sample_dir.exists():
            shutil.rmtree(sample_dir)
            return f"Deleted voice sample: {voice_name}"
        
        # Check clones directory
        clone_dir = self.path_manager.get_voice_clones_path() / voice_name
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
            return f"Deleted voice clone: {voice_name}"
        
        raise ValueError(f"Voice not found: {voice_name}")

    def generate_speech(self, text: str, voice_name: str) -> str:
        """Generate speech from text using specified voice."""
        # Process text
        chunks = self.text_processor.process(text)
        
        # Get voice profile
        voice = self.voice_manager.get_voice_config(voice_name)
        if not voice:
            raise ValueError(f"Voice '{voice_name}' not found")
            
        # Generate audio
        output_path = self.path_manager.get_output_path() / f"{voice_name}_{int(time.time())}.wav"
        self.tts_engine.generate(
            text=chunks,
            voice=voice,
            output_path=output_path
        )
        
        return str(output_path)
        
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices."""
        profiles = self.voice_manager.get_profiles()
        return [{"name": p.voice_name, "description": p.description, "exaggeration": p.exaggeration} for p in profiles]

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize a name for use in filenames.
        
        Args:
            name: Name to sanitize
            
        Returns:
            str: Sanitized name
        """
        if not name:
            return ""
        # Replace spaces and special characters with underscores
        safe_name = "".join(c if c.isalnum() else "_" for c in name.lower())
        # Remove consecutive underscores
        while "__" in safe_name:
            safe_name = safe_name.replace("__", "_")
        # Remove leading/trailing underscores
        return safe_name.strip("_") 