import runpod
import torch
import base64
import io
import json
import tempfile
import os
from pathlib import Path
from audiobook.tts.engine import TTSEngine
from audiobook.tts.text_processor import chunk_text_by_sentences
from audiobook.voice_management import VoiceManager
from audiobook.config.paths import PathManager
import logging
from typing import Dict, Any

# Global variables to cache components
tts_engine = None
voice_manager = None
path_manager = None

# Configure logging
logger = logging.getLogger("RunPodHandler")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

def initialize_components():
    """Initialize the TTS engine and voice manager if not already loaded"""
    global tts_engine, voice_manager, path_manager
    if tts_engine is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts_engine = TTSEngine(device=device)
        path_manager = PathManager()
        
        # Set up voice library paths
        voice_library = path_manager.voice_library_dir
        voice_library.mkdir(parents=True, exist_ok=True)
        (voice_library / "clones").mkdir(exist_ok=True)
        (voice_library / "output").mkdir(exist_ok=True)
        (voice_library / "samples").mkdir(exist_ok=True)
        
        voice_manager = VoiceManager(voice_library)
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
    logger.info("Starting voice cloning process")
    logger.debug(f"Job input: {input_data.keys()}")
    
    try:
        # Initialize components
        logger.debug("Initializing components...")
        _, voice_mgr, paths = initialize_components()
        logger.info("Components initialized successfully")
        
        # Extract parameters
        logger.debug("Extracting parameters from job input...")
        reference_audio = base64.b64decode(input_data["reference_audio"])
        voice_name = input_data["voice_name"]
        display_name = input_data.get("display_name", voice_name)
        description = input_data.get("description", "")
        parameters = input_data.get("parameters", {})
        
        logger.info(f"Processing voice clone request for: {voice_name}")
        logger.debug(f"Parameters: display_name={display_name}, parameters={parameters}")
        
        # Save reference audio temporarily
        logger.debug("Saving reference audio to temporary file...")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(reference_audio)
            temp_path = temp_file.name
            logger.debug(f"Audio saved to: {temp_path}")
        
        try:
            # Validate audio sample
            logger.debug("Validating audio sample...")
            is_valid, message = voice_mgr.validate_voice_sample(temp_path)
            if not is_valid:
                logger.error(f"Audio validation failed: {message}")
                raise ValueError(message)
            logger.info("Audio sample validated successfully")
            
            # Save voice profile
            logger.debug("Saving voice profile...")
            result = voice_mgr.save_voice_profile(
                voice_name,
                display_name,
                description,
                temp_path,
                parameters=parameters
            )
            success = True
            message = result
            logger.info(f"Voice profile saved successfully: {message}")
            
        except Exception as e:
            logger.error(f"Error during voice cloning: {str(e)}", exc_info=True)
            success = False
            message = str(e)
            raise
        
        finally:
            # Clean up temporary file
            logger.debug("Cleaning up temporary files...")
            try:
                os.unlink(temp_path)
                logger.debug("Temporary files cleaned up successfully")
            except Exception as e:
                logger.warning(f"Error cleaning up temporary file: {str(e)}")
    
    except Exception as e:
        logger.error(f"Voice cloning failed: {str(e)}", exc_info=True)
        return {"success": False, "message": str(e)}
    
    return {"success": success, "message": message}

def handler(job):
    """Main handler for RunPod requests"""
    job_type = job["input"]["type"]
    logger.info(f"Received job of type: {job_type}")
    
    try:
        if job_type == "tts":
            return generate_tts(job)
        elif job_type == "clone":
            return clone_voice(job)
        else:
            error_msg = f"Unknown job type: {job_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    except Exception as e:
        logger.error(f"Error processing job: {str(e)}", exc_info=True)
        return {"error": str(e)}

runpod.serverless.start({"handler": handler}) 