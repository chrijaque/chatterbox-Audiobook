"""
Voice management utilities for audiobook generation.

Handles voice profile CRUD operations, voice library management, and voice selection.
"""

import os
import json
import time
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import librosa
import soundfile as sf
from .tts.audio_processor import AudioProcessor
from .models import VoiceProfile, RunPodJobInput
from .config import PathManager, settings

# Import RunPod client without system checks
try:
    from .api.runpod_client import RunPodClient
    RUNPOD_AVAILABLE = True
except Exception as e:
    print(f"Warning: RunPod client import failed ({str(e)})")
    RUNPOD_AVAILABLE = False


class VoiceManager:
    def __init__(self, voice_library_path: Optional[str] = None):
        """Initialize voice manager with path to voice library"""
        self.path_manager = PathManager(voice_library_path)
        self.audio_processor = AudioProcessor()
        
        # Initialize RunPod client if configured
        self.runpod_client = None
        if settings.is_runpod_configured:
            try:
                self.runpod_client = RunPodClient(
                    api_key=settings.RUNPOD_API_KEY,
                    endpoint_id=settings.ENDPOINT_ID
                )
            except Exception as e:
                print(f"Warning: Failed to initialize RunPod client ({str(e)})")

    def get_voice_profiles(self) -> List[VoiceProfile]:
        """Get list of all available voice profiles"""
        profiles = []
        clones_dir = self.path_manager.get_voice_clones_path()
        
        if not clones_dir.exists():
            return profiles
            
        for voice_dir in clones_dir.iterdir():
            if not voice_dir.is_dir():
                continue
                
            profile = self.get_voice_profile(voice_dir.name)
            if profile:
                profiles.append(profile)
        return profiles

    def get_voice_profile(self, voice_name: str) -> Optional[VoiceProfile]:
        """Get a specific voice profile by name"""
        voice_dir = self.path_manager.get_voice_clones_path() / voice_name
        config_file = voice_dir / "config.json"
        
        if not config_file.exists():
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
                    "audio_file": str(voice_dir / "reference.wav"),
                    "exaggeration": config.get("exaggeration", 0.5),
                    "cfg_weight": config.get("cfg_weight", 0.5),
                    "temperature": config.get("temperature", 0.8),
                    "created_date": config_file.stat().st_ctime,
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
        audio_file: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        normalization_enabled: bool = False,
        target_level_db: float = -18.0
    ) -> str:
        """Save a voice profile with reference audio.
        
        Args:
            name: Name/ID for the voice
            display_name: Display name (defaults to name)
            description: Optional description
            audio_file: Path to audio file
            exaggeration: Voice emotion exaggeration (0-1)
            cfg_weight: Classifier-free guidance weight (0-1)
            temperature: Generation temperature (0-1)
            normalization_enabled: Whether to normalize audio
            target_level_db: Target audio level in dB
            
        Returns:
            str: Success message
        """
        if not audio_file:
            raise ValueError("No audio file provided")
            
        # Validate audio file
        valid, message = self.validate_voice_sample(audio_file)
        if not valid:
            raise ValueError(f"Invalid voice sample: {message}")
            
        # Create safe name
        safe_name = self._sanitize_name(name)
        if not safe_name:
            raise ValueError("Invalid voice name")
            
        # Create voice directory
        voice_dir = self.path_manager.get_voice_samples_path() / safe_name
        voice_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy and process reference audio
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        target_audio = voice_dir / f"sample_{timestamp}.wav"
        shutil.copy2(audio_file, target_audio)
        
        # Create metadata
        metadata = {
            "name": safe_name,
            "display_name": display_name or name,
            "description": description or "",
            "audio_file": str(target_audio),
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "temperature": temperature,
            "created_date": time.time(),
            "normalization_enabled": normalization_enabled,
            "target_level_db": target_level_db,
            "normalization_applied": False,
            "original_level_info": None,
            "version": "2.0"
        }
        
        # Apply normalization if enabled
        if normalization_enabled:
            try:
                audio_data, sample_rate = sf.read(target_audio)
                original_info = self.audio_processor.get_audio_info(audio_data)
                normalized_audio = self.audio_processor.normalize_audio(audio_data, target_level_db)
                sf.write(target_audio, normalized_audio, sample_rate)
                
                metadata["normalization_applied"] = True
                metadata["original_level_info"] = original_info
                
            except Exception as e:
                print(f"Warning: Failed to normalize audio: {str(e)}")
        
        # Save metadata
        metadata_path = voice_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        return f"Voice sample '{name}' saved successfully"

    def delete_voice_profile(self, voice_name: str) -> Tuple[str, List[VoiceProfile]]:
        """Delete a voice profile"""
        voice_dir = self.path_manager.get_voice_clones_path() / voice_name
        
        if not voice_dir.exists():
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
            
            # Check sample rate (16kHz minimum)
            if sample_rate < 16000:
                return False, f"Sample rate must be at least 16kHz (got {sample_rate}Hz)"
            
            # Check channels (mono only)
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                return False, "Audio must be mono (single channel)"
            
            return True, "Voice sample is valid"
            
        except Exception as e:
            return False, f"Error validating audio file: {str(e)}"

    def get_voice_choices(self) -> List[str]:
        """Get list of voice names for UI selection"""
        return [p.display_name for p in self.get_voice_profiles()]

    def get_audiobook_voice_choices(self) -> List[str]:
        """Get list of voice names suitable for audiobook narration"""
        return [p.display_name for p in self.get_voice_profiles() 
                if not p.description or "audiobook" in p.description.lower()]

    def get_voice_config(self, voice_name: str) -> Optional[Dict[str, Any]]:
        """Get voice configuration for TTS"""
        profile = self.get_voice_profile(voice_name)
        if not profile:
            return None
        return profile.dict()

    def find_voice_file(self, voice_name: str) -> Optional[str]:
        """Find reference audio file for a voice"""
        profile = self.get_voice_profile(voice_name)
        if not profile or not profile.audio_file:
            return None
        return profile.audio_file

    def load_voice_for_tts(self, voice_name: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Load voice data and config for TTS generation"""
        profile = self.get_voice_profile(voice_name)
        if not profile:
            return None, {}
            
        return profile.audio_file, profile.dict()

    def refresh_voice_list(self) -> List[str]:
        """Refresh and return list of available voices"""
        return [p.name for p in self.get_voice_profiles()]

    def create_assignment_interface(self, voice_counts: Dict[str, int]) -> List[Any]:
        """Create voice assignment interface for UI"""
        choices = self.get_voice_choices()
        # Interface creation logic here
        return []  # TODO: Implement interface creation

    def clone_voice(
        self,
        audio_path: str,
        name: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, str]:
        """Clone a voice using RunPod.
        
        Args:
            audio_path: Path to reference audio file
            name: Name for the cloned voice
            description: Optional description
            parameters: Optional parameters for voice cloning
                - exaggeration: Voice emotion exaggeration (0-1)
                - cfg_weight: Classifier-free guidance weight (0-1)
                - temperature: Generation temperature (0-1)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        print(f"\nVoiceManager.clone_voice called with:")
        print(f"  audio_path: {audio_path}")
        print(f"  name: {name}")
        print(f"  description: {description}")
        print(f"  parameters: {parameters}")
        
        if not self.runpod_client:
            print("  Error: RunPod client not configured")
            return False, "RunPod not configured. Please set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID"
            
        # Validate audio file
        valid, message = self.validate_voice_sample(audio_path)
        if not valid:
            print(f"  Error: Invalid voice sample - {message}")
            return False, f"Invalid voice sample: {message}"
            
        # Create safe name
        safe_name = self._sanitize_name(name)
        if not safe_name:
            print("  Error: Invalid voice name")
            return False, "Invalid voice name"
            
        print(f"  Using safe name: {safe_name}")
        
        # Create voice directory
        voice_dir = self.path_manager.get_voice_clones_path() / safe_name
        voice_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created voice directory: {voice_dir}")
        
        # Copy reference audio
        ref_audio = voice_dir / "reference.wav"
        shutil.copy2(audio_path, ref_audio)
        print(f"  Copied reference audio to: {ref_audio}")
        
        try:
            # Submit cloning job
            print(f"  Submitting voice cloning job for {safe_name}...")
            success, message = self.runpod_client.clone_voice(
                audio_path=str(ref_audio),
                voice_name=safe_name,
                display_name=name,
                description=description,
                parameters=parameters or {}
            )
            
            print(f"  RunPod response: success={success}, message={message}")
            
            if not success:
                # Clean up on failure
                print("  Cleaning up voice directory due to failure")
                shutil.rmtree(voice_dir)
                return False, message
                
            return True, f"Voice '{name}' cloned successfully"
            
        except Exception as e:
            # Clean up on failure
            print(f"  Exception in clone_voice: {str(e)}")
            print("  Cleaning up voice directory due to exception")
            shutil.rmtree(voice_dir)
            return False, str(e)

    def _sanitize_name(self, name: str) -> str:
        """Create a safe filename from a display name"""
        # Remove invalid characters and spaces
        safe = "".join(c.lower() if c.isalnum() else "_" for c in name)
        # Remove consecutive underscores
        while "__" in safe:
            safe = safe.replace("__", "_")
        # Remove leading/trailing underscores
        return safe.strip("_")


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


def check_runpod_config() -> Tuple[bool, str]:
    """Check if RunPod is properly configured"""
    if not settings.RUNPOD_API_KEY or not settings.ENDPOINT_ID:
        return False, "RunPod not configured. Please set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID environment variables."
    return True, "" 