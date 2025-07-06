"""
Voice management utilities for audiobook generation.

Handles voice profile CRUD operations, voice library management, and voice selection.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any


def ensure_voice_library_exists(voice_library_path: str) -> None:
    """Ensure the voice library directory exists.
    
    Args:
        voice_library_path: Path to voice library directory
    """
    os.makedirs(voice_library_path, exist_ok=True)


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


def save_voice_profile(
    voice_library_path: str,
    voice_name: str,
    audio_data: bytes,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs
) -> str:
    """Save a new voice profile.
    
    Args:
        voice_library_path: Path to voice library directory
        voice_name: Name for the voice profile
        audio_data: Raw audio data bytes
        display_name: Display name for the voice
        description: Description of the voice
        **kwargs: Additional profile settings
        
    Returns:
        Name of saved voice profile
    """
    # Sanitize voice name
    safe_name = "".join(c.lower() if c.isalnum() else "_" for c in voice_name)
    
    # Create profile directory
    voice_path = Path(voice_library_path) / safe_name
    voice_path.mkdir(parents=True, exist_ok=True)
    
    # Save audio file
    audio_path = voice_path / "voice.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_data)
    
    # Save config
    config = {
        "voice_name": safe_name,
        "display_name": display_name or voice_name,
        "description": description,
        "audio_file": "voice.wav",
        **kwargs
    }
    
    config_path = voice_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    return safe_name


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