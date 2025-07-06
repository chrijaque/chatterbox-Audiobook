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
from audiobook.tts.engine import TTSEngine
from audiobook.tts.text_processor import chunk_text_by_sentences
from audiobook.voice_management import VoiceManager

# Initialize Firebase
cred = credentials.Certificate(os.environ.get('FIREBASE_CREDENTIALS'))
firebase_admin.initialize_app(cred, {
    'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET')
})
bucket = storage.bucket()

# Global variables to cache components
tts_engine = None
voice_manager = None

def initialize_components():
    """Initialize the TTS engine and voice manager if not already loaded"""
    global tts_engine, voice_manager
    if tts_engine is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts_engine = TTSEngine(device=device)
        voice_manager = VoiceManager(os.environ.get('VOICE_LIBRARY_PATH', 'voice_library'))
    return tts_engine, voice_manager

def save_to_firebase(audio_data, filename):
    """Save audio data to Firebase Storage"""
    blob = bucket.blob(f'tts_output/{filename}')
    blob.upload_from_string(audio_data, content_type='audio/wav')
    return blob.public_url

def generate_tts(job):
    """Generate TTS audio from text"""
    input_data = job["input"]
    
    # Initialize components
    engine, voice_mgr = initialize_components()
    
    # Extract parameters
    text = input_data["text"]
    voice_name = input_data.get("voice_name")
    params = input_data.get("parameters", {})
    
    # Load voice profile
    audio_file, exaggeration, cfg_weight, temperature, message = voice_mgr.load_voice_profile(voice_name)
    if audio_file is None:
        raise ValueError(message)
    
    # Generate audio chunks
    audio_chunks = engine.generate_tts(
        text,
        audio_file,
        chunk_size=50,  # Default chunk size
        exaggeration=exaggeration,
        temperature=temperature,
        cfg_weight=cfg_weight
    )
    
    # Combine chunks
    final_audio = engine.audio_processor.combine_audio_chunks(audio_chunks)
    
    # Save to temporary WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        engine.audio_processor.save_audio_chunks([final_audio], "temp", os.path.dirname(temp_file.name))
        with open(temp_file.name, 'rb') as f:
            audio_data = f.read()
        os.unlink(temp_file.name)
    
    # Convert audio data to base64
    audio_base64 = base64.b64encode(audio_data).decode()
    
    return {
        "audio_data": audio_base64,
        "content_type": "audio/wav"
    }

def clone_voice(job):
    """Clone a voice from reference audio"""
    input_data = job["input"]
    
    # Initialize components
    _, voice_mgr = initialize_components()
    
    # Extract parameters
    reference_audio = base64.b64decode(input_data["reference_audio"])
    voice_name = input_data["voice_name"]
    display_name = input_data.get("display_name", voice_name)
    description = input_data.get("description", "")
    
    # Save reference audio temporarily
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(reference_audio)
        temp_path = temp_file.name
    
    # Clone voice
    try:
        # Validate audio sample
        is_valid, message = voice_mgr.validate_voice_sample(temp_path)
        if not is_valid:
            raise ValueError(message)
            
        # Save voice profile
        result = voice_mgr.save_voice_profile(
            voice_name,
            display_name,
            description,
            temp_path
        )
        success = True
        message = result
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