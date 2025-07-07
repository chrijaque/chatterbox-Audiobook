"""
Audiobook generation package

A modular audiobook creation system using TTS technology.
"""

__version__ = "1.0.0"
__author__ = "ChatterBox Team"

from .config import settings
from .tts import AudiobookTTS
from .voice_management import *

__all__ = [
    "settings",
    "AudiobookTTS"
] 