"""Default configuration values for the audiobook application"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any

# Text processing
MAX_WORDS_PER_CHUNK = 50  # Maximum number of words per chunk for TTS
MAX_CHARS_PER_CHUNK = 250  # Maximum characters per chunk
MIN_CHUNK_LENGTH = 10  # Minimum number of words per chunk

class TextPreset(str, Enum):
    """Text processing presets"""
    AUDIOBOOK = "audiobook"  # Optimized for long-form content
    DIALOGUE = "dialogue"    # Optimized for conversations
    NARRATION = "narration" # Optimized for storytelling

@dataclass
class ProjectPreset:
    """Project configuration preset"""
    name: str = "default"
    description: str = "Default project settings"
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}

# Audio processing
SAMPLE_RATE = 24000  # Hz
HOP_LENGTH = 256     # For audio feature extraction
N_FFT = 2048        # FFT window size
N_MELS = 80         # Number of mel bands

# Voice settings
DEFAULT_VOICE_CONFIG = {
    "exaggeration": 0.5,    # Voice emotion exaggeration (0.0-1.0)
    "cfg_weight": 0.5,      # Classifier-free guidance weight (0.0-1.0)
    "temperature": 0.8,     # Generation temperature (0.0-1.0)
}

# Output formats
SUPPORTED_FORMATS = ["wav", "mp3"]
DEFAULT_FORMAT = "wav"

# Chunking strategies
CHUNK_ON_PUNCTUATION = [
    ".", "!", "?",         # Sentence endings
    ";", ":",              # Major breaks
    ",", "-", "—",        # Minor breaks
]

CHUNK_MERGE_THRESHOLD = 0.7  # Threshold for merging small chunks
