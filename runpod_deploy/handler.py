import runpod
import torch
import base64
import io
import json
import tempfile
import os
from pathlib import Path
from chatterbox.tts import ChatterboxTTS
from audiobook.tts.engine import TTSEngine
from audiobook.tts.text_processor import chunk_text_by_sentences
from audiobook.voice_management import VoiceManager
from audiobook.config.paths import PathManager

# Global variables to cache components
tts_engine = None
voice_manager = None
path_manager = None

def initialize_components():
    """Initialize the TTS engine and voice manager if not already loaded"""
    global tts_engine, voice_manager, path_manager
    if tts_engine is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts_engine = TTSEngine(device=device)
        path_manager = PathManager()
        voice_manager = VoiceManager(path_manager.voice_library_dir)
    return tts_engine, voice_manager, path_manager

def generate_tts(job):
    """Generate TTS audio from text"""
    input_data = job["input"]
    
    # Initialize components
    engine, voice_mgr, paths = initialize_components()
    
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
    
    # Save to output directory with unique name
    output_path = paths.get_tts_output_path() / f"{voice_name}_{hash(text)[:8]}.wav"
    engine.audio_processor.save_audio_chunks([final_audio], output_path)
    
    # Read the saved file and convert to base64
    with open(output_path, 'rb') as f:
        audio_data = f.read()
    audio_base64 = base64.b64encode(audio_data).decode()
    
    return {
        "audio_data": audio_base64,
        "content_type": "audio/wav"
    }

def clone_voice(job):
    """Clone a voice from reference audio"""
    input_data = job["input"]
    
    # Initialize components
    _, voice_mgr, paths = initialize_components()
    
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