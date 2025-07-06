import runpod
import torch
import base64
import io
import json
import tempfile
import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, storage
from chatterbox.tts import ChatterboxTTS
from audiobook.processing import chunk_text_by_sentences, parse_multi_voice_text
from audiobook.voice_management import save_voice_profile

# Initialize Firebase
cred = credentials.Certificate(os.environ.get('FIREBASE_CREDENTIALS'))
firebase_admin.initialize_app(cred, {
    'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET')
})
bucket = storage.bucket()

# Global variables to cache models
tts_model = None
device = None

def initialize_model():
    """Initialize the TTS model if not already loaded"""
    global tts_model, device
    if tts_model is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tts_model = ChatterboxTTS(device=device)
    return tts_model

def save_to_firebase(audio_data, filename):
    """Save audio data to Firebase Storage"""
    blob = bucket.blob(f'tts_output/{filename}')
    blob.upload_from_string(audio_data, content_type='audio/wav')
    return blob.public_url

def generate_tts(job):
    """Generate TTS audio from text"""
    input_data = job["input"]
    
    # Initialize model
    model = initialize_model()
    
    # Extract parameters
    text = input_data["text"]
    voice_name = input_data.get("voice_name")
    params = input_data.get("parameters", {})
    
    # Extract generation parameters with defaults
    exaggeration = params.get("exaggeration", 0.5)
    temperature = params.get("temperature", 0.8)
    cfg_weight = params.get("cfg_weight", 0.5)
    min_p = params.get("min_p", 0.05)
    top_p = params.get("top_p", 1.0)
    repetition_penalty = params.get("repetition_penalty", 1.2)
    
    # Generate audio with parameters
    audio_data = model.generate_speech(
        text, 
        voice_name=voice_name,
        exaggeration=exaggeration,
        temperature=temperature,
        cfg_weight=cfg_weight,
        min_p=min_p,
        top_p=top_p,
        repetition_penalty=repetition_penalty
    )
    
    # Convert audio data to base64
    audio_base64 = base64.b64encode(audio_data).decode()
    
    return {
        "audio_data": audio_base64,
        "content_type": "audio/wav"
    }

def clone_voice(job):
    """Clone a voice from reference audio"""
    input_data = job["input"]
    
    # Initialize model
    model = initialize_model()
    
    # Extract parameters
    reference_audio = base64.b64decode(input_data["reference_audio"])
    voice_name = input_data["voice_name"]
    
    # Save reference audio temporarily
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(reference_audio)
        temp_path = temp_file.name
    
    # Clone voice
    try:
        save_voice_profile(temp_path, voice_name)
        success = True
        message = f"Voice {voice_name} cloned successfully"
    except Exception as e:
        success = False
        message = str(e)
    finally:
        os.unlink(temp_path)
    
    return {"success": success, "message": message}

def handler(job):
    """Main handler for RunPod requests"""
    job_type = job["input"]["type"]
    
    try:
        if job_type == "tts":
            return generate_tts(job)
        elif job_type == "clone":
            return clone_voice(job)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler}) 