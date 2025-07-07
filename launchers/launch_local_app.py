#!/usr/bin/env python3
"""
Local-only launcher for Chatterbox TTS Audiobook Edition
Security: Local access only (127.0.0.1:7860)
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from audiobook.launcher import launch_app
    
    if __name__ == "__main__":
        print("🔒 Launching in LOCAL ONLY mode...")
        print("📍 Finding available port (starting from 7860)...")
        print("🚫 No network or public access enabled")
        
        launch_app(
            mode="ui",
            host="127.0.0.1",
            port=None,  # Let the app find an available port
            share=False
        )

except Exception as e:
    print(f"❌ Error launching application: {e}")
    print("📁 Make sure you're in the correct directory and the environment is set up properly")
    input("Press Enter to exit...") 