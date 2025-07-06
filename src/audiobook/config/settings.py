"""
Global settings and configuration for the audiobook TTS system.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Audio Settings
SAMPLE_RATE = 24000
DEFAULT_TARGET_LEVEL_DB = -18.0
DEFAULT_SILENCE_THRESHOLD = -50.0
DEFAULT_MIN_SILENCE_DURATION = 0.5

# Text Processing
MAX_WORDS_PER_CHUNK = 50
DEFAULT_EXAGGERATION = 0.5
DEFAULT_TEMPERATURE = 0.8
DEFAULT_CFG_WEIGHT = 0.5

# Project Settings
DEFAULT_AUTOSAVE_INTERVAL = 10
CHUNKS_PER_PAGE = 50
DEFAULT_OUTPUT_FORMAT = "wav"

# Voice Library
VOICE_LIBRARY_PATH = os.getenv("VOICE_LIBRARY_PATH", "voice_library")
VOICE_SAMPLES_PATH = Path(VOICE_LIBRARY_PATH) / "samples"
VOICE_CLONES_PATH = Path(VOICE_LIBRARY_PATH) / "clones"
VOICE_OUTPUT_PATH = Path(VOICE_LIBRARY_PATH) / "output"
VOICE_CONFIG_FILENAME = "config.json"

# Project Storage
PROJECT_ROOT = "audiobook_projects"
PROJECT_METADATA_FILENAME = "metadata.json"
TEMP_DIR = "temp"

# Memory Management
MIN_REQUIRED_MEMORY = 4 * 1024 * 1024 * 1024  # 4GB in bytes
MEMORY_CHECK_INTERVAL = 60  # seconds

# Model Settings
DEFAULT_DEVICE = "cuda" if os.getenv("FORCE_CPU", "0") != "1" else "cpu"
MODEL_CHECKPOINT_DIR = "checkpoints"

# Multi-voice Settings
MAX_CHARACTERS = 6
CHARACTER_MARKER_START = "["
CHARACTER_MARKER_END = "]"
NARRATOR_TAG = "[Narrator]"

# Batch Processing
MAX_BATCH_SIZE = 10
MAX_CONCURRENT_PROCESSES = 4

# RunPod Settings
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_TIMEOUT = 300  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Check if RunPod is configured
is_runpod_configured = bool(RUNPOD_API_KEY and ENDPOINT_ID) 