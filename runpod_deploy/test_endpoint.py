import runpod
import base64
import os

# Initialize RunPod
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "ekfmpp6tfjgc4v")  # New endpoint ID
runpod.api_key = RUNPOD_API_KEY

def test_tts():
    """Test TTS generation"""
    print("Testing TTS generation...")
    
    # Create endpoint instance
    endpoint = runpod.Endpoint(ENDPOINT_ID)
    
    # Use the correct run_sync method
    response = endpoint.run_sync({
        "type": "tts",
        "text": "Hello, this is a test of the text to speech system.",
        "voice_name": None  # Using default voice
    })
    
    print("Response:", response)
    
    # Save the audio if successful
    if response and "output" in response and response["output"] and "audio_data" in response["output"]:
        audio_data = base64.b64decode(response["output"]["audio_data"])
        with open("test_output.wav", "wb") as f:
            f.write(audio_data)
        print("Audio saved to test_output.wav")
    elif response and "error" in response:
        print(f"Error: {response['error']}")
    else:
        print("No audio data in response")

if __name__ == "__main__":
    test_tts() 