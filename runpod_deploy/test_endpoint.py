import runpod
import base64
import os

# Initialize RunPod
RUNPOD_API_KEY = "***REMOVED***"
ENDPOINT_ID = "ekfmpp6tfjgc4v"  # New endpoint ID
runpod.api_key = RUNPOD_API_KEY

def test_tts():
    """Test TTS generation"""
    print("Testing TTS generation...")
    
    response = runpod.run(
        endpoint_id=ENDPOINT_ID,
        input={
            "type": "tts",
            "text": "Hello, this is a test of the text to speech system.",
            "voice_name": None  # Using default voice
        }
    )
    
    print("Response:", response)
    
    # Save the audio if successful
    if "audio_data" in response:
        audio_data = base64.b64decode(response["audio_data"])
        with open("test_output.wav", "wb") as f:
            f.write(audio_data)
        print("Audio saved to test_output.wav")

if __name__ == "__main__":
    test_tts() 