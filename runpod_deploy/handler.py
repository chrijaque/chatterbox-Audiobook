import runpod
import torch
import base64
import numpy as np
import os
import json
import tempfile
import soundfile as sf
import torchaudio as ta
from pathlib import Path

# Optional Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    print("Firebase not available - continuing without Firebase support")
    FIREBASE_AVAILABLE = False

# Add src directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audiobook.tts import TTSEngine
from audiobook.voice_management import VoiceManager
from audiobook.config import settings

# Import ChatterboxVC for voice conversion
try:
    from chatterbox.vc import ChatterboxVC
    VOICE_CONVERSION_AVAILABLE = True
    print("ChatterboxVC available for voice conversion")
except ImportError:
    VOICE_CONVERSION_AVAILABLE = False
    print("Warning: ChatterboxVC not available. Voice conversion disabled.")

# Initialize components (lazy initialization to prevent startup crashes)
tts_engine = None
voice_manager = None

def get_tts_engine():
    """Get or initialize TTS engine."""
    global tts_engine
    if tts_engine is None:
        try:
            tts_engine = TTSEngine()
            print("✅ TTS engine initialized successfully")
        except Exception as e:
            print(f"❌ TTS engine initialization failed: {e}")
            raise
    return tts_engine

def get_voice_manager():
    """Get or initialize voice manager."""
    global voice_manager
    if voice_manager is None:
        try:
            voice_manager = VoiceManager(voice_library_path=settings.VOICE_LIBRARY_PATH)
            print("✅ Voice manager initialized successfully")
        except Exception as e:
            print(f"❌ Voice manager initialization failed: {e}")
            raise
    return voice_manager

# Initialize Firebase if available and credentials exist
bucket = None
if FIREBASE_AVAILABLE and os.path.exists("firebase-credentials.json"):
    try:
        cred = credentials.Certificate("firebase-credentials.json")
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
        })
        bucket = storage.bucket()
        print("Firebase initialized successfully")
    except Exception as e:
        print(f"Firebase initialization failed: {e}")
        bucket = None
else:
    print("Firebase not available or credentials not found")

def handler(event):
    """Handle RunPod serverless requests."""
    try:
        # Validate event structure
        if not isinstance(event, dict) or "input" not in event:
            return {"error": "Invalid event structure - 'input' key required", "success": False}
        
        # Extract parameters
        input_data = event["input"]
        if not isinstance(input_data, dict):
            return {"error": "Invalid input data - must be a dictionary", "success": False}
            
        request_type = input_data.get("type", "tts")
        
        print(f"Processing request type: {request_type}")
        
        if request_type == "tts":
            return handle_tts_request(input_data)
        elif request_type == "voice_clone":
            return handle_voice_clone_request(input_data)
        elif request_type == "voice_convert":
            return handle_voice_conversion_request(input_data)
        else:
            return {"error": f"Unknown request type: {request_type}. Supported types: tts, voice_clone, voice_convert", "success": False}
            
    except KeyError as e:
        return {"error": f"Missing required key: {str(e)}", "success": False}
    except Exception as e:
        print(f"Handler error: {str(e)}")
        return {"error": str(e), "success": False}

def handle_tts_request(input_data):
    """Handle TTS generation request."""
    text = input_data.get("text", "")
    voice_name = input_data.get("voice_name", "")
    
    if not text:
        return {"error": "Text is required", "success": False}
    if not voice_name:
        return {"error": "Voice name is required", "success": False}
    
    try:
        # Get initialized components
        vm = get_voice_manager()
        tts = get_tts_engine()
        
        # Load voice profile
        audio_file, voice_profile = vm.load_voice_for_tts(voice_name)
        if not audio_file:
            return {"error": f"Voice file not found for {voice_name}", "success": False}
        
        # Ensure model is loaded (only if not already loaded)
        if not hasattr(tts, 'model') or tts.model is None:
            tts.load_model()
        
        # Generate audio with retry and CPU fallback
        wav, device_used = tts.generate_with_retry(
            text=text,
            audio_prompt_path=audio_file,
            exaggeration=voice_profile.exaggeration,
            temperature=voice_profile.temperature,
            cfg_weight=voice_profile.cfg_weight
        )
        
        # Save to temporary file
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "output.wav")
        sf.write(output_path, wav, tts.sample_rate)
        
        # Convert to base64 for response
        with open(output_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode()
        
        # Clean up
        os.remove(output_path)
        os.rmdir(temp_dir)
        
        return {
            "audio_data": audio_data,
            "sample_rate": tts.sample_rate,
            "device_used": device_used,
            "success": True
        }
        
    except Exception as e:
        print(f"TTS generation error: {str(e)}")
        return {"error": f"TTS generation failed: {str(e)}", "success": False}

def handle_voice_clone_request(input_data):
    """Handle voice cloning request."""
    voice_name = input_data.get("voice_name", "")
    audio_data_b64 = input_data.get("audio_data", "")
    description = input_data.get("description", "")
    exaggeration = input_data.get("exaggeration", 0.5)
    cfg_weight = input_data.get("cfg_weight", 0.5)
    temperature = input_data.get("temperature", 0.8)
    
    if not voice_name:
        return {"error": "Voice name is required", "success": False}
    if not audio_data_b64:
        return {"error": "Audio data is required", "success": False}
    
    try:
        # Decode audio data
        audio_data = base64.b64decode(audio_data_b64)
            
        # Save voice profile
        vm = get_voice_manager()
        vm.save_profile(
            voice_name=voice_name,
            audio_data=audio_data,
            display_name=voice_name,
            description=description,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature
        )
        
        return {
            "message": f"Voice '{voice_name}' cloned successfully",
            "success": True
        }
        
    except Exception as e:
        return {"error": f"Failed to clone voice: {str(e)}", "success": False}

def handle_voice_conversion_request(input_data):
    """Handle voice conversion request using ChatterboxVC."""
    if not VOICE_CONVERSION_AVAILABLE:
        return {"error": "Voice conversion not available - ChatterboxVC not installed", "success": False}
    
    source_audio_b64 = input_data.get("source_audio", "")
    target_voice_name = input_data.get("target_voice_name", "")
    output_name = input_data.get("output_name", "converted_audio")
    
    if not source_audio_b64:
        return {"error": "Source audio data is required", "success": False}
    if not target_voice_name:
        return {"error": "Target voice name is required", "success": False}
    
    try:
        # Auto-detect device
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        print(f"Using device for voice conversion: {device}")
        
        # Create temporary files for processing
        temp_dir = tempfile.mkdtemp()
        source_audio_path = os.path.join(temp_dir, "source_audio.wav")
        
        # Decode and save source audio
        source_audio_data = base64.b64decode(source_audio_b64)
        with open(source_audio_path, "wb") as f:
            f.write(source_audio_data)
        
        # Find target voice file
        vm = get_voice_manager()
        target_voice_path = vm.find_voice_file(target_voice_name)
        if not target_voice_path:
            return {"error": f"Target voice file not found for: {target_voice_name}", "success": False}
        
        # Initialize ChatterboxVC model
        print("Loading ChatterboxVC model...")
        vc_model = ChatterboxVC.from_pretrained(device)
        
        # Perform voice conversion
        print(f"Converting {source_audio_path} to sound like {target_voice_name}")
        converted_wav = vc_model.generate(
            audio=source_audio_path,
            target_voice_path=target_voice_path
        )
        
        # Save converted audio to temporary file
        output_path = os.path.join(temp_dir, f"{output_name}.wav")
        ta.save(output_path, converted_wav, vc_model.sr)
        
        # Convert to base64 for response
        with open(output_path, "rb") as f:
            converted_audio_b64 = base64.b64encode(f.read()).decode()
        
        # Clean up temporary files
        os.remove(source_audio_path)
        os.remove(output_path)
        os.rmdir(temp_dir)
        
        return {
            "audio_data": converted_audio_b64,
            "sample_rate": vc_model.sr,
            "message": f"Voice conversion completed: {output_name}",
            "success": True
        }
        
    except Exception as e:
        # Clean up on error
        try:
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
        except:
            pass
        
        print(f"Voice conversion error: {str(e)}")
        return {"error": f"Failed to convert voice: {str(e)}", "success": False}

if __name__ == "__main__":
    print("🚀 Starting RunPod handler...")
    print(f"📁 Voice library path: {settings.VOICE_LIBRARY_PATH}")
    print(f"🔥 Firebase available: {FIREBASE_AVAILABLE}")
    print(f"🎤 Voice conversion available: {VOICE_CONVERSION_AVAILABLE}")

    print("🌐 Starting RunPod serverless handler...")
    print("⏳ Waiting for requests...")

runpod.serverless.start({"handler": handler}) 