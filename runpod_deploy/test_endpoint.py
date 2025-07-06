#!/usr/bin/env python3

import runpod
import base64
import os
from pathlib import Path
from typing import Optional
from audiobook.config import settings
from audiobook.config.paths import PathManager

class RunPodTester:
    def __init__(self):
        """Initialize RunPod tester with configuration"""
        # Verify environment variables
        if not settings.RUNPOD_API_KEY:
            raise ValueError("RUNPOD_API_KEY not set in environment")
        if not settings.ENDPOINT_ID:
            raise ValueError("RUNPOD_ENDPOINT_ID not set in environment")
            
        # Initialize RunPod client
        self.endpoint = runpod.Endpoint(settings.ENDPOINT_ID, api_key=settings.RUNPOD_API_KEY)
        print("\n✅ Initialized with:")
        print(f"  - Endpoint ID: {settings.ENDPOINT_ID}")
        
        # Initialize path manager
        self.paths = PathManager()
        print(f"  - Voice Library: {self.paths.voice_library_dir}")
        
    def test_voice_clone(self, sample_path: str, voice_name: str) -> bool:
        """Test voice cloning with a sample audio file"""
        print(f"\nTesting voice cloning:")
        print(f"  - Sample: {sample_path}")
        print(f"  - Voice name: {voice_name}")
        
        try:
            # Read and encode audio file
            with open(sample_path, "rb") as f:
                audio_data = f.read()
            audio_b64 = base64.b64encode(audio_data).decode()
            
            # Submit cloning job
            response = self.endpoint.run({
                "type": "clone",
                "reference_audio": audio_b64,
                "voice_name": voice_name,
                "display_name": voice_name,
                "description": "Test voice clone"
            })
            
            if "error" in response:
                print(f"❌ Error: {response['error']}")
                return False
                
            print("✅ Voice cloning successful")
            print(f"  - Message: {response.get('message', 'No message')}")
            
            # Verify voice was saved
            voice_path = self.paths.get_voice_path(voice_name)
            if not voice_path.exists():
                print(f"❌ Voice directory not created at {voice_path}")
                return False
                
            print(f"✅ Voice saved to {voice_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
    
    def test_tts(self, text: str, voice_name: str) -> bool:
        """Test TTS generation with a voice"""
        print(f"\nTesting TTS generation:")
        print(f"  - Text: {text}")
        print(f"  - Voice: {voice_name}")
        
        try:
            response = self.endpoint.run({
                "type": "tts",
                "text": text,
                "voice_name": voice_name,
                "parameters": {
                    "exaggeration": 0.5,
                    "temperature": 0.8,
                    "cfg_weight": 0.5
                }
            })
            
            if "error" in response:
                print(f"❌ Error: {response['error']}")
                return False
            
            if "audio_data" not in response:
                print("❌ No audio data in response")
                return False
            
            # Save the audio to output directory
            audio_data = base64.b64decode(response["audio_data"])
            output_path = self.paths.get_tts_output_path() / f"test_{voice_name}.wav"
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            print("✅ TTS generation successful")
            print(f"  - Output saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

def main():
    """Run the test suite"""
    try:
        tester = RunPodTester()
    except ValueError as e:
        print(f"❌ Setup failed: {str(e)}")
        return
    
    # Test voice cloning with existing sample
    sample_path = Path("voice_library/samples/chris rp test.wav")
    if not sample_path.exists():
        print(f"\n⚠️  Sample not found at {sample_path}")
        return
        
    print(f"\nUsing sample: {sample_path}")
    success = tester.test_voice_clone(str(sample_path), "chris_test_voice")
    if success:
        # If cloning worked, test TTS
        tester.test_tts(
            "This is a test of the text to speech system using the RunPod API.",
            "chris_test_voice"
        )

if __name__ == "__main__":
    main() 