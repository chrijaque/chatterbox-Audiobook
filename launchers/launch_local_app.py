#!/usr/bin/env python3
"""
Local-only launcher for Chatterbox TTS Audiobook Edition
Security: Local access only (127.0.0.1:7860)
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audiobook.ui.app import create_ui
from audiobook.tts import AudiobookTTS
from audiobook.config import settings

if __name__ == "__main__":
    print("🔒 Launching in LOCAL ONLY mode...")
    print("📍 Finding available port (starting from 7860)...")
    print("🚫 No network or public access enabled")
    
    # Initialize TTS engine with RunPod if configured
    use_runpod = settings.is_runpod_configured
    if use_runpod:
        print("✨ RunPod configured:")
        api_key_preview = settings.RUNPOD_API_KEY[:8] if settings.RUNPOD_API_KEY else "Not Set"
        print(f"  API Key: {api_key_preview}...")
        print(f"  Endpoint: {settings.ENDPOINT_ID}")
    else:
        print("⚠️  RunPod not configured, using local TTS engine")
    
    tts_engine = AudiobookTTS(use_runpod=use_runpod)
    
    # Create and launch UI
    app = create_ui(tts_engine)
    app.queue(
        max_size=50,
        concurrency_count=1
    ).launch(
        share=False,
        server_name="127.0.0.1", 
        server_port=None,  # Let Gradio find an available port
        inbrowser=True  # Auto-open browser
    ) 