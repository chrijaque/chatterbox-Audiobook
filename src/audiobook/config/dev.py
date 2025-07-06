"""Development configuration for the audiobook application"""

import os
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).parent.parent.parent.parent
VOICE_LIBRARY_PATH = os.path.join(ROOT_DIR, "voice_library")
SAMPLES_PATH = os.path.join(VOICE_LIBRARY_PATH, "samples")
CLONES_PATH = os.path.join(VOICE_LIBRARY_PATH, "clones")
OUTPUT_PATH = os.path.join(VOICE_LIBRARY_PATH, "output")

# Server configuration
API_HOST = "localhost"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"

# UI configuration
UI_HOST = "localhost"
UI_PORT = 7860
UI_URL = f"http://{UI_HOST}:{UI_PORT}"

# Create required directories
for path in [VOICE_LIBRARY_PATH, SAMPLES_PATH, CLONES_PATH, OUTPUT_PATH]:
    os.makedirs(path, exist_ok=True) 