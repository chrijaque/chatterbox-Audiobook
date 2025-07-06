"""
Voice management utilities for audiobook generation.

Handles voice profile CRUD operations, voice library management, and voice selection.
"""

import os
import json
import time
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import librosa
import soundfile as sf
from .tts.audio_processor import AudioProcessor
from .models import VoiceProfile


class VoiceManager:
    def __init__(self, voice_library_path: str):
        """Initialize voice manager with path to voice library"""
        self.voice_library_path = voice_library_path
        self.clones_path = os.path.join(voice_library_path, "clones")
        self.audio_processor = AudioProcessor()
        
        # Create directories if they don't exist
        os.makedirs(self.voice_library_path, exist_ok=True)
        os.makedirs(self.clones_path, exist_ok=True)

    def get_voice_profiles(self) -> List[VoiceProfile]:
        """Get list of all available voice profiles"""
        profiles = []
        for voice_name in os.listdir(self.clones_path):
            profile = self.get_voice_profile(voice_name)
            if profile:
                profiles.append(profile)
        return profiles

    def get_voice_profile(self, voice_name: str) -> Optional[VoiceProfile]:
        """Get a specific voice profile by name"""
        voice_dir = os.path.join(self.clones_path, voice_name)
        config_file = os.path.join(voice_dir, "config.json")
        
        if not os.path.exists(config_file):
            return None
            
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Convert legacy format if needed
            if isinstance(config, dict) and "audio_file" not in config:
                config = {
                    "name": voice_name,
                    "display_name": voice_name,
                    "description": None,
                    "audio_file": os.path.join(voice_dir, "reference.wav"),
                    "exaggeration": config.get("exaggeration", 0.5),
                    "cfg_weight": config.get("cfg_weight", 0.5),
                    "temperature": config.get("temperature", 0.8),
                    "created_date": os.path.getctime(config_file),
                    "normalization_enabled": config.get("normalization_enabled", False),
                    "target_level_db": config.get("target_level_db", -18.0),
                    "normalization_applied": config.get("normalization_applied", False),
                    "original_level_info": config.get("original_level_info", None),
                    "version": "2.0"
                }
                
            return VoiceProfile(**config)
            
        except Exception as e:
            print(f"Error loading voice profile {voice_name}: {str(e)}")
            return None

    def save_voice_profile(
        self,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        audio_file: str = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        normalization_enabled: bool = False,
        target_level_db: float = -18.0
    ) -> str:
        """Save a voice profile with reference audio"""
        if not audio_file:
            return "Error: No audio file provided"
            
        # Create voice directory
        voice_dir = os.path.join(self.clones_path, name)
        os.makedirs(voice_dir, exist_ok=True)
        
        # Copy and process reference audio
        target_audio = os.path.join(voice_dir, "reference.wav")
        shutil.copy2(audio_file, target_audio)
        
        # Create profile
        profile = VoiceProfile(
            name=name,
            display_name=display_name or name,
            description=description,
            audio_file=target_audio,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
            created_date=time.time(),
            normalization_enabled=normalization_enabled,
            target_level_db=target_level_db,
            normalization_applied=False,
            original_level_info=None,
            version="2.0"
        )
        
        # Apply normalization if enabled
        if normalization_enabled:
            try:
                audio_data, sample_rate = sf.read(target_audio)
                original_info = self.audio_processor.get_audio_info(audio_data)
                normalized_audio = self.audio_processor.normalize_audio(audio_data, target_level_db)
                sf.write(target_audio, normalized_audio, sample_rate)
                
                profile.normalization_applied = True
                profile.original_level_info = original_info
                
            except Exception as e:
                print(f"Warning: Failed to normalize audio: {str(e)}")
        
        # Save config
        config_file = os.path.join(voice_dir, "config.json")
        with open(config_file, 'w') as f:
            json.dump(profile.dict(), f, indent=2)
            
        return f"Voice profile '{name}' created successfully"

    def delete_voice_profile(self, voice_name: str) -> Tuple[str, List[VoiceProfile]]:
        """Delete a voice profile"""
        voice_dir = os.path.join(self.clones_path, voice_name)
        
        if not os.path.exists(voice_dir):
            return f"Voice profile '{voice_name}' not found", self.get_voice_profiles()
            
        try:
            shutil.rmtree(voice_dir)
            return f"Voice profile '{voice_name}' deleted successfully", self.get_voice_profiles()
        except Exception as e:
            return f"Error deleting voice profile: {str(e)}", self.get_voice_profiles()

    def validate_voice_sample(self, audio_file: str) -> Tuple[bool, str]:
        """Validate a voice sample file"""
        try:
            audio_data, sample_rate = sf.read(audio_file)
            
            # Check duration (5-30 seconds)
            duration = len(audio_data) / sample_rate
            if duration < 5 or duration > 30:
                return False, f"Audio duration must be between 5-30 seconds (got {duration:.1f}s)"
            
            # Check sample rate (16kHz minimum)
            if sample_rate < 16000:
                return False, f"Sample rate must be at least 16kHz (got {sample_rate}Hz)"
            
            # Check channels (mono only)
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                return False, "Audio must be mono (single channel)"
            
            return True, "Voice sample is valid"
            
        except Exception as e:
            return False, f"Error validating audio file: {str(e)}"


def get_voice_profiles(voice_library_path: str) -> List[Dict[str, Any]]:
    """Get list of available voice profiles.
    
    Args:
        voice_library_path: Path to voice library directory
        
    Returns:
        List of voice profile dictionaries
    """
    profiles = []
    library_path = Path(voice_library_path)
    
    if not library_path.exists():
        return profiles
    
    for item in library_path.iterdir():
        if not item.is_dir():
            continue
        
        config_path = item / "config.json"
        if not config_path.exists():
            continue
        
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            profiles.append(config)
        except Exception:
            continue
    
    return profiles


def get_voice_choices(voice_library_path: str) -> List[str]:
    """Get list of available voice names for UI dropdowns.
    
    Args:
        voice_library_path: Path to voice library directory
        
    Returns:
        List of voice names
    """
    profiles = get_voice_profiles(voice_library_path)
    return [profile['voice_name'] for profile in profiles]


def get_audiobook_voice_choices(voice_library_path: str) -> List[str]:
    """Get voice choices formatted for audiobook interface.
    
    Args:
        voice_library_path: Path to voice library directory
        
    Returns:
        List of voice names with display formatting
    """
    choices = get_voice_choices(voice_library_path)
    if not choices:
        return ["No voices available - Please add voices first"]
    return choices


def get_voice_config(voice_library_path: str, voice_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific voice.
    
    Args:
        voice_library_path: Path to voice library directory
        voice_name: Name of voice to get config for
        
    Returns:
        Voice configuration dictionary or None if not found
    """
    voice_path = Path(voice_library_path) / voice_name
    config_path = voice_path / "config.json"
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def find_voice_file(voice_library_path: str, voice_name: str) -> Optional[str]:
    """Find the voice audio file for a profile.
    
    Args:
        voice_library_path: Path to voice library directory
        voice_name: Name of voice to find file for
        
    Returns:
        Path to voice audio file or None if not found
    """
    voice_path = Path(voice_library_path) / voice_name
    
    if not voice_path.exists():
        return None
    
    # Check common extensions
    for ext in [".wav", ".mp3", ".ogg"]:
        audio_path = voice_path / f"voice{ext}"
        if audio_path.exists():
            return str(audio_path)
    
    return None


def load_voice_for_tts(voice_library_path: str, voice_name: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Load voice audio file and configuration for TTS generation.
    
    Args:
        voice_library_path: Path to voice library directory
        voice_name: Name of the voice to load
        
    Returns:
        tuple: (audio_file_path, voice_config)
    """
    if not voice_name:
        return None, {}
    
    profile_dir = Path(voice_library_path) / voice_name
    if not profile_dir.exists():
        return None, {}
    
    # Look for audio file
    audio_file = None
    for ext in ['.wav', '.mp3', '.flac']:
        potential_file = profile_dir / f"voice{ext}"
        if potential_file.exists():
            audio_file = str(potential_file)
            break
    
    # Get voice configuration
    config = get_voice_config(voice_library_path, voice_name)
    
    return audio_file, config


def load_voice_profile(voice_library_path: str, voice_name: str) -> Tuple[str, str, str, float, float, float]:
    """Load voice profile data for editing.
    
    Args:
        voice_library_path: Path to voice library directory
        voice_name: Name of voice to load
        
    Returns:
        tuple: (display_name, description, audio_path, exaggeration, cfg_weight, temperature)
    """
    if not voice_name:
        return "", "", "", 1.0, 1.0, 0.7
    
    config = get_voice_config(voice_library_path, voice_name)
    audio_file, _ = load_voice_for_tts(voice_library_path, voice_name)
    
    return (
        config.get('display_name', voice_name),
        config.get('description', ''),
        audio_file or "",
        config.get('exaggeration', 1.0),
        config.get('cfg_weight', 1.0),
        config.get('temperature', 0.7)
    )


def delete_voice_profile(voice_library_path: str, voice_name: str) -> bool:
    """Delete a voice profile.
    
    Args:
        voice_library_path: Path to voice library directory
        voice_name: Name of voice to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    if not voice_name:
        return False
    
    voice_path = Path(voice_library_path) / voice_name
    
    if not voice_path.exists():
        return False
    
    try:
        shutil.rmtree(voice_path)
        return True
    except Exception:
        return False


def refresh_voice_list(voice_library_path: str) -> List[str]:
    """Refresh and return the current voice list.
    
    Args:
        voice_library_path: Path to voice library directory
        
    Returns:
        Updated list of voice names
    """
    return get_voice_choices(voice_library_path)


def refresh_voice_choices(voice_library_path: str) -> List[str]:
    """Refresh voice choices for regular dropdowns.
    
    Args:
        voice_library_path: Path to voice library directory
        
    Returns:
        Updated list of voice choices
    """
    return get_voice_choices(voice_library_path)


def refresh_audiobook_voice_choices(voice_library_path: str) -> List[str]:
    """Refresh voice choices for audiobook interface.
    
    Args:
        voice_library_path: Path to voice library directory
        
    Returns:
        Updated list of audiobook voice choices
    """
    return get_audiobook_voice_choices(voice_library_path)


def create_assignment_interface_with_dropdowns(
    voice_counts: Dict[str, int], 
    voice_library_path: str
) -> List[Any]:
    """Create voice assignment interface components.
    
    Args:
        voice_counts: Dictionary mapping character names to word counts
        voice_library_path: Path to voice library directory
        
    Returns:
        List of interface components
    """
    # This would typically return Gradio components
    # For now, return character names and available voices
    characters = list(voice_counts.keys())
    available_voices = get_voice_choices(voice_library_path)
    
    # Return data that can be used to create dropdowns
    return [
        {
            'character': char,
            'word_count': voice_counts[char],
            'available_voices': available_voices
        }
        for char in characters[:6]  # Limit to 6 characters
    ] 