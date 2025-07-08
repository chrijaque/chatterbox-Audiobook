"""
Voice management utilities for audiobook generation.

Handles voice profile CRUD operations, voice library management, and voice selection.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import torch
import torchaudio as ta
import tempfile

# Check if RunPod is available for voice cloning
try:
    from .api.runpod_client import RunPodClient
    from .config import settings
    RUNPOD_AVAILABLE = settings.is_runpod_configured
    if RUNPOD_AVAILABLE:
        print("RunPod available for voice cloning")
    else:
        print("RunPod not configured - voice cloning will be limited")
except ImportError as e:
    print(f"Import error: {e}")
    RUNPOD_AVAILABLE = False
    print("Warning: RunPod client not available. Voice cloning disabled.")

@dataclass
class VoiceProfile:
    """Voice profile data."""
    voice_name: str
    display_name: str
    description: Optional[str] = None
    audio_file: Optional[str] = None
    exaggeration: float = 0.5
    temperature: float = 0.8
    cfg_weight: float = 0.5
    created_date: str = ""
    voice_type: str = "sample"  # "sample" or "clone"
    
    def __post_init__(self):
        """Handle any additional parameters that might be in config files."""
        # This allows the dataclass to accept extra parameters without failing
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceProfile':
        """Create VoiceProfile from dictionary, filtering out unknown parameters."""
        # Get only the fields that VoiceProfile actually has
        import dataclasses
        valid_fields = {field.name for field in dataclasses.fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # Ensure required fields are present
        if 'voice_name' not in filtered_data:
            # Use display_name as voice_name if voice_name is missing
            filtered_data['voice_name'] = filtered_data.get('display_name', 'unknown')
        
        if 'display_name' not in filtered_data:
            filtered_data['display_name'] = filtered_data.get('voice_name', 'Unknown Voice')
        
        # Set default voice_type if not present
        if 'voice_type' not in filtered_data:
            filtered_data['voice_type'] = 'sample'
        
        return cls(**filtered_data)

@dataclass
class TTSGenerationSettings:
    """Settings for TTS generation."""
    exaggeration: float = 0.5
    temperature: float = 0.8
    cfg_weight: float = 0.5

@dataclass
class AudioProcessingSettings:
    """Settings for audio processing."""
    enable_normalization: bool = True
    target_level_db: float = -18.0

class VoiceManager:
    """Manager for voice profiles and operations."""
    
    def __init__(self, voice_library_path: str):
        self.voice_library_path = voice_library_path
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        base_path = Path(self.voice_library_path)
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (base_path / "samples").mkdir(exist_ok=True)
        (base_path / "clones").mkdir(exist_ok=True)
        (base_path / "output").mkdir(exist_ok=True)
        (base_path / "output" / "tts").mkdir(exist_ok=True)
        
        # Migrate existing voices from root directory
        self._migrate_existing_voices()
    
    def _migrate_existing_voices(self):
        """Migrate existing voices from root directory to appropriate subdirectories."""
        base_path = Path(self.voice_library_path)
        
        # Find all directories in root that contain config.json but are not our standard directories
        standard_dirs = {"samples", "clones", "output", "audiobook_projects", "test"}
        
        for item in base_path.iterdir():
            if (item.is_dir() and 
                item.name not in standard_dirs and 
                (item / "config.json").exists()):
                
                try:
                    # Read the config
                    with open(item / "config.json", 'r') as f:
                        config = json.load(f)
                    
                    # Determine if this is a clone or sample based on parameters
                    # If it has custom parameters (not defaults), treat as clone
                    has_custom_params = (
                        config.get('exaggeration', 0.5) != 0.5 or
                        config.get('cfg_weight', 0.5) != 0.5 or
                        config.get('temperature', 0.8) != 0.8
                    )
                    
                    target_dir = "clones" if has_custom_params else "samples"
                    destination = base_path / target_dir / item.name
                    
                    # Only migrate if destination doesn't exist
                    if not destination.exists():
                        print(f"Migrating voice '{item.name}' to {target_dir}/")
                        shutil.move(str(item), str(destination))
                        
                        # Update config with voice_type
                        config['voice_type'] = 'clone' if has_custom_params else 'sample'
                        if 'created_date' not in config:
                            config['created_date'] = datetime.now().isoformat()
                        
                        with open(destination / "config.json", 'w') as f:
                            json.dump(config, f, indent=2)
                    
            except Exception as e:
                    print(f"Error migrating voice '{item.name}': {e}")
                    continue

    def get_profiles(self) -> List[VoiceProfile]:
        """Get all voice profiles from samples and clones directories."""
        profiles = []
        base_path = Path(self.voice_library_path)
        
        # Get samples
        samples_dir = base_path / "samples"
        if samples_dir.exists():
            for profile_dir in samples_dir.iterdir():
                if profile_dir.is_dir():
                    config_path = profile_dir / "config.json"
                    if config_path.exists():
                        try:
                            with open(config_path, 'r') as f:
                                config = json.load(f)
                            config['voice_type'] = 'sample'
                            profile = VoiceProfile.from_dict(config)
                            profiles.append(profile)
                        except Exception as e:
                            print(f"Error loading profile {profile_dir.name}: {e}")
        
        # Get clones
        clones_dir = base_path / "clones"
        if clones_dir.exists():
            for profile_dir in clones_dir.iterdir():
                if profile_dir.is_dir():
                    config_path = profile_dir / "config.json"
                    if config_path.exists():
                        try:
                            with open(config_path, 'r') as f:
                                config = json.load(f)
                            config['voice_type'] = 'clone'
                            profile = VoiceProfile.from_dict(config)
                            profiles.append(profile)
                        except Exception as e:
                            print(f"Error loading profile {profile_dir.name}: {e}")
        
        return profiles

    def get_voice_choices(self) -> List[str]:
        """Get list of voice names for dropdowns."""
        return [profile.voice_name for profile in self.get_profiles()]

    def get_audiobook_voice_choices(self) -> List[str]:
        """Get list of voice names for audiobook interface."""
        return [profile.voice_name for profile in self.get_profiles()]

    def get_voice_config(self, voice_name: str) -> Optional[VoiceProfile]:
        """Get voice configuration by name."""
        profiles = self.get_profiles()
        for profile in profiles:
            if profile.voice_name == voice_name:
                return profile
        return None

    def find_voice_file(self, voice_name: str) -> Optional[str]:
        """Find voice audio file by name."""
        base_path = Path(self.voice_library_path)
        
        # Check samples directory
        samples_dir = base_path / "samples" / voice_name
        if samples_dir.exists():
            for ext in [".wav", ".mp3", ".ogg", ".flac"]:
                audio_path = samples_dir / f"voice{ext}"
                if audio_path.exists():
                    return str(audio_path)
        
        # Check clones directory
        clones_dir = base_path / "clones" / voice_name
        if clones_dir.exists():
            for ext in [".wav", ".mp3", ".ogg", ".flac"]:
                audio_path = clones_dir / f"voice{ext}"
                if audio_path.exists():
                    return str(audio_path)
        
            return None
            
    def load_voice_for_tts(self, voice_name: str) -> Tuple[Optional[str], VoiceProfile]:
        """Load voice for TTS generation."""
        audio_file = self.find_voice_file(voice_name)
        config = self.get_voice_config(voice_name)
        
        if config is None:
            # Create a default config if none exists
            config = VoiceProfile(
                voice_name=voice_name,
                display_name=voice_name,
                voice_type="sample"
            )
        
        return audio_file, config

    def save_sample(
        self,
        voice_name: str,
        audio_data: bytes,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> str:
        """Save a voice sample to the samples directory."""
        return self._save_voice(
            voice_name=voice_name,
            audio_data=audio_data,
            voice_type="sample",
            display_name=display_name,
            description=description,
            **kwargs
        )

    def clone_voice(
        self,
        voice_name: str,
        audio_data: bytes,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        perform_actual_cloning: bool = False,
        source_audio_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """Clone a voice with specific parameters to the clones directory.
        
        Args:
            voice_name: Name for the cloned voice
            audio_data: Raw audio data bytes for the target voice
            display_name: Display name for the voice
            description: Description of the voice
            exaggeration: Exaggeration parameter
            cfg_weight: CFG weight parameter
            temperature: Temperature parameter
            perform_actual_cloning: Whether to perform actual voice conversion
            source_audio_path: Path to source audio for voice conversion
            **kwargs: Additional parameters
            
        Returns:
            Name of the cloned voice
        """
        # Save the voice profile first
        safe_name = self._save_voice(
            voice_name=voice_name,
            audio_data=audio_data,
            voice_type="clone",
            display_name=display_name,
            description=description,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
            **kwargs
        )
        
        # Perform actual voice cloning if requested and available
        if perform_actual_cloning and RUNPOD_AVAILABLE and source_audio_path:
            try:
                cloned_audio_path = self.perform_voice_cloning(
                    source_audio_path=source_audio_path,
                    target_voice_name=safe_name
                )
                print(f"Voice cloning completed: {cloned_audio_path}")
            except Exception as e:
                print(f"Voice cloning failed, but profile saved: {e}")
        
        return safe_name

    def perform_voice_cloning(
        self,
        source_audio_path: str,
        target_voice_name: str,
        device: Optional[str] = None
    ) -> str:
        """Perform actual voice cloning using RunPod.
        
        Args:
            source_audio_path: Path to the source audio to be converted
            target_voice_name: Name of the target voice profile
            device: Device to use for inference (ignored for RunPod)
            
        Returns:
            Path to the cloned audio file
        """
        if not RUNPOD_AVAILABLE:
            raise ValueError("Voice cloning not available. RunPod not configured.")
        
        print(f"Performing voice cloning via RunPod: {source_audio_path} -> {target_voice_name}")
        
        # Initialize RunPod client
        client = RunPodClient(
            api_key=settings.RUNPOD_API_KEY,
            endpoint_id=settings.ENDPOINT_ID
        )
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{target_voice_name}_cloned_{timestamp}"
        
        # Perform voice conversion via RunPod
        audio_data, error_msg = client.convert_voice(
            source_audio_path=source_audio_path,
            target_voice_name=target_voice_name,
            output_name=output_name
        )
        
        if error_msg:
            raise ValueError(f"RunPod voice conversion failed: {error_msg}")
        
        if not audio_data:
            raise ValueError("No audio data received from RunPod")
        
        # Save the cloned audio locally
        base_path = Path(self.voice_library_path)
        output_dir = base_path / "clones" / target_voice_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_filename = f"cloned_audio_{timestamp}.wav"
        output_path = output_dir / output_filename
        
        # Save the audio data
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        return str(output_path)

    def clone_voice_from_files(
        self,
        source_audio_path: str,
        target_voice_name: str,
        output_name: str,
        device: Optional[str] = None
    ) -> str:
        """Clone voice using RunPod with target voice name.
        
        Args:
            source_audio_path: Path to source audio to be converted
            target_voice_name: Name of target voice profile
            output_name: Name for the output
            device: Device to use for inference (ignored for RunPod)
        
        Returns:
            Path to the cloned audio file
        """
        if not RUNPOD_AVAILABLE:
            raise ValueError("Voice cloning not available. RunPod not configured.")
        
        print(f"Performing voice cloning via RunPod: {source_audio_path} -> {target_voice_name}")
        
        # Verify target voice exists
        if not self.find_voice_file(target_voice_name):
            raise ValueError(f"Target voice not found: {target_voice_name}")
        
        # Initialize RunPod client
        client = RunPodClient(
            api_key=settings.RUNPOD_API_KEY,
            endpoint_id=settings.ENDPOINT_ID
        )
        
        # Perform voice conversion via RunPod
        audio_data, error_msg = client.convert_voice(
            source_audio_path=source_audio_path,
            target_voice_name=target_voice_name,
            output_name=output_name
        )
        
        if error_msg:
            raise ValueError(f"RunPod voice conversion failed: {error_msg}")
        
        if not audio_data:
            raise ValueError("No audio data received from RunPod")
        
        # Save to output directory
        base_path = Path(self.voice_library_path)
        output_dir = base_path / "output" / "tts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create output filename
        safe_name = "".join(c.lower() if c.isalnum() else "_" for c in output_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{safe_name}_cloned_{timestamp}.wav"
        output_path = output_dir / output_filename
        
        # Save the audio data
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        return str(output_path)

    def _save_voice(
        self,
        voice_name: str,
        audio_data: bytes,
        voice_type: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> str:
        """Internal method to save voice to appropriate directory."""
        # Sanitize voice name
        safe_name = "".join(c.lower() if c.isalnum() else "_" for c in voice_name)
        
        # Determine target directory
        base_path = Path(self.voice_library_path)
        if voice_type == "clone":
            target_dir = base_path / "clones"
        else:
            target_dir = base_path / "samples"
        
        # Create profile directory
        voice_path = target_dir / safe_name
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
            "voice_type": voice_type,
            "created_date": datetime.now().isoformat(),
            **kwargs
        }
        
        config_path = voice_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        return safe_name

    def save_profile(
        self,
        voice_name: str,
        audio_data: bytes,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> str:
        """Save a voice profile (backwards compatibility - saves as sample)."""
        return self.save_sample(
            voice_name=voice_name,
            audio_data=audio_data,
            display_name=display_name,
                description=description,
            **kwargs
        )

    def load_profile(self, voice_name: str) -> VoiceProfile:
        """Load voice profile by name."""
        config = self.get_voice_config(voice_name)
        if config:
            return config
        
        # Return default if not found
        return VoiceProfile(
            voice_name=voice_name,
            display_name=voice_name,
            voice_type="sample"
        )

    def delete_profile(self, voice_name: str) -> bool:
        """Delete a voice profile."""
        base_path = Path(self.voice_library_path)
        
        # Check samples directory
        samples_path = base_path / "samples" / voice_name
        if samples_path.exists():
            try:
                shutil.rmtree(samples_path)
                return True
            except Exception:
                pass
        
        # Check clones directory
        clones_path = base_path / "clones" / voice_name
        if clones_path.exists():
            try:
                shutil.rmtree(clones_path)
                return True
            except Exception:
                pass
        
        return False

    def refresh_voice_list(self) -> List[str]:
        """Refresh voice list."""
        return self.get_voice_choices()

    def refresh_voice_choices(self) -> List[str]:
        """Refresh voice choices."""
        return self.get_voice_choices()

    def refresh_audiobook_voice_choices(self) -> List[str]:
        """Refresh audiobook voice choices."""
        return self.get_audiobook_voice_choices()

    def create_assignment_interface(self, voice_counts: Dict[str, int]) -> List[Any]:
        """Create voice assignment interface."""
        characters = list(voice_counts.keys())
        available_voices = self.get_voice_choices()
        
        return [
            {
                'character': char,
                'word_count': voice_counts[char],
                'available_voices': available_voices
            }
            for char in characters[:6]
        ]

# Keep existing utility functions below
def ensure_voice_library_exists(voice_library_path: str) -> None:
    """Ensure the voice library directory exists."""
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
            # Add voice_name from directory name if not present
            if 'voice_name' not in config:
                config['voice_name'] = item.name
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