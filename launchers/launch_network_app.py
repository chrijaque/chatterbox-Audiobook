#!/usr/bin/env python3
"""
Network launcher for Chatterbox TTS Audiobook Edition
Security: Local network access (0.0.0.0:7860)
"""

import sys
import os
import socket

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audiobook.ui.app import create_ui
from audiobook.tts import AudiobookTTS
from audiobook.config import settings

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote server to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "Unable to determine IP"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("🏠 Launching in NETWORK mode...")
    print("📍 Finding available port (starting from 7860)...")
    print(f"🌐 Your network IP: {local_ip}")
    print("🚫 No public sharing enabled")
    
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
        server_name="0.0.0.0", 
        server_port=None,  # Let Gradio find an available port
        inbrowser=True  # Auto-open browser
    ) 