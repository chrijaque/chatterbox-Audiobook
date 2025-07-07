"""Configuration settings for the application."""
import os
import json
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from .config.settings import RUNPOD_API_KEY, ENDPOINT_ID, RUNPOD_TIMEOUT, MAX_RETRIES, RETRY_DELAY

# Load environment variables from .env file first, so they take precedence
load_dotenv(override=True)

class Settings:
    """Application settings."""
    
    def __init__(self):
        """Initialize settings."""
        # Base paths
        self.BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.VOICE_LIBRARY_PATH = self.BASE_DIR / "voice_library"
        
        # Voice management paths
        self.VOICE_SAMPLES_PATH = self.VOICE_LIBRARY_PATH / "samples"
        self.VOICE_CLONES_PATH = self.VOICE_LIBRARY_PATH / "clones"
        self.TTS_OUTPUT_PATH = self.VOICE_LIBRARY_PATH / "output"
        
        # Create directories if they don't exist
        self.VOICE_LIBRARY_PATH.mkdir(parents=True, exist_ok=True)
        self.VOICE_SAMPLES_PATH.mkdir(parents=True, exist_ok=True)
        self.VOICE_CLONES_PATH.mkdir(parents=True, exist_ok=True)
        self.TTS_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        
        # Server settings
        self.HOST = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
        self.PORT = int(os.getenv("GRADIO_SERVER_PORT", 7860))
        
        # Model settings
        self.DEVICE = os.getenv("DEVICE", "cpu")
        self.MODEL_DIR = self.BASE_DIR / "models"
        
        # Import RunPod settings from settings module
        self.RUNPOD_API_KEY = RUNPOD_API_KEY
        self.ENDPOINT_ID = ENDPOINT_ID
        self.RUNPOD_TIMEOUT = RUNPOD_TIMEOUT
        self.MAX_RETRIES = MAX_RETRIES
        self.RETRY_DELAY = RETRY_DELAY
        
        # Application settings
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # Sample rate for audio processing
        self.SAMPLE_RATE: int = 24000
    
    @property
    def is_runpod_configured(self) -> bool:
        """Check if RunPod is configured."""
        return bool(self.RUNPOD_API_KEY and self.ENDPOINT_ID)
    
    def get_voice_choices(self) -> List[str]:
        """Get list of available voice clones."""
        if not self.VOICE_CLONES_PATH.exists():
            return []
        
        voices = []
        for voice_dir in self.VOICE_CLONES_PATH.iterdir():
            if voice_dir.is_dir() and (voice_dir / "config.json").exists():
                voices.append(voice_dir.name)
        return sorted(voices)
    
    def get_voice_samples(self) -> List[str]:
        """Get list of available voice samples."""
        if not self.VOICE_SAMPLES_PATH.exists():
            return []
        
        samples = []
        for sample_file in self.VOICE_SAMPLES_PATH.glob("*.wav"):
            samples.append(sample_file.name)
        return sorted(samples)
    
    def get_voice_path(self, voice_name: str) -> Optional[Path]:
        """Get path to a specific voice clone directory."""
        voice_path = self.VOICE_CLONES_PATH / voice_name
        if voice_path.exists() and voice_path.is_dir():
            return voice_path
        return None

# Global settings instance
settings = Settings()

# Default configuration values
DEFAULT_VOICE_LIBRARY = "voice_library"
CONFIG_FILE = "audiobook_config.json"


def load_config() -> str:
    """Load configuration including voice library path.
    
    Returns:
        str: Path to the voice library directory
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return config.get('voice_library_path', DEFAULT_VOICE_LIBRARY)
        except Exception:
            return DEFAULT_VOICE_LIBRARY
    return DEFAULT_VOICE_LIBRARY


def save_config(voice_library_path: str) -> str:
    """Save configuration including voice library path.
    
    Args:
        voice_library_path: Path to the voice library directory
        
    Returns:
        str: Success or error message
    """
    config = {
        'voice_library_path': voice_library_path,
        'last_updated': str(Path().resolve())  # timestamp
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return f"✅ Configuration saved - Voice library path: {voice_library_path}"
    except Exception as e:
        return f"❌ Error saving configuration: {str(e)}"


def update_voice_library_path(new_path: str) -> tuple[str, str]:
    """Update the voice library path in configuration.
    
    Args:
        new_path: New path to the voice library
        
    Returns:
        tuple: (status_message, updated_path)
    """
    if not new_path.strip():
        return "❌ Voice library path cannot be empty", ""
    
    # Create directory if it doesn't exist
    try:
        os.makedirs(new_path, exist_ok=True)
        save_result = save_config(new_path)
        return save_result, new_path
    except Exception as e:
        return f"❌ Error updating voice library path: {str(e)}", "" 