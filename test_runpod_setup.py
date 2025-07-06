#!/usr/bin/env python3

import os
from audiobook.api.runpod_client import RunPodClient
from audiobook.config import settings

def test_runpod_configuration():
    """Test if RunPod is properly configured"""
    print("Testing RunPod Configuration...")
    
    # Check environment variables
    api_key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    
    if not api_key:
        print("❌ RUNPOD_API_KEY not set")
        return False
    if not endpoint_id:
        print("❌ RUNPOD_ENDPOINT_ID not set")
        return False
    
    print("✅ Environment variables found")
    
    # Test RunPod client initialization
    try:
        client = RunPodClient(api_key, endpoint_id)
        print("✅ RunPod client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize RunPod client: {str(e)}")
        return False
    
    # Test simple TTS generation
    try:
        print("\nTesting TTS generation...")
        audio_data, error = client.generate_speech(
            "This is a test of the text to speech system.",
            "default"
        )
        if error:
            print(f"❌ TTS generation failed: {error}")
            return False
        if audio_data:
            print("✅ TTS generation successful")
    except Exception as e:
        print(f"❌ TTS generation failed: {str(e)}")
        return False
    
    print("\nAll tests passed! RunPod is configured correctly.")
    return True

if __name__ == "__main__":
    success = test_runpod_configuration()
    exit(0 if success else 1) 