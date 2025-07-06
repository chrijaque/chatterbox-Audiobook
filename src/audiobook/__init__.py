"""
Audiobook generation package

A modular audiobook creation system using TTS technology.
"""

__version__ = "1.0.0"
__author__ = "ChatterBox Team"

from .tts import AudiobookTTS as ChatterboxTTS
from .voice_management import *
from .project_management import *
from .audio_processing import *
from .config import *
from .processing import * 