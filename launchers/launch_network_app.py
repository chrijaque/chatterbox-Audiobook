#!/usr/bin/env python3
"""
Network-enabled launcher for Chatterbox TTS Audiobook Edition
Security: Network access enabled (0.0.0.0:port)
"""

import sys
import os
import socket

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from audiobook.launcher import launch_app

if __name__ == "__main__":
        print("\n🌐 Launching in NETWORK mode...")
        print("⚠️  WARNING: Network access enabled!")
    print("📍 Finding available port (starting from 7860)...")
        
        # Get local IP for display
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"📡 Local network access will be available at: http://{local_ip}:7860")
        
        launch_app(
            mode="ui",
            host="0.0.0.0",  # Allow network access
            port=None,  # Let the app find an available port
            share=True  # Enable sharing
        )

except Exception as e:
    print(f"❌ Error launching application: {e}")
    print("📁 Make sure you're in the correct directory and the environment is set up properly")
    input("Press Enter to exit...") 