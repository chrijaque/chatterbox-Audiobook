"""
RunPod-based TTS module for audiobook generation
"""
import runpod
import base64
import numpy as np
import torch
import librosa
import os
from typing import Optional, Dict, Any

# RunPod configuration
RUNPOD_API_KEY = "***REMOVED***"
ENDPOINT_ID = "ekfmpp6tfjgc4v"
runpod.api_key = RUNPOD_API_KEY

class AudiobookTTS:
    """Text-to-Speech interface using RunPod backend"""
    
    def __init__(self, device="cpu"):
        self.device = device
        self.sr = 24000  # sample rate of synthesized audio
        self.current_voice_id = None
        self.current_voice_config = {}

    @classmethod
    def from_pretrained(cls, device="cpu") -> 'AudiobookTTS':
        """Factory method to create TTS instance"""
        return cls(device=device)

    def generate(self, text: str, conds=None, exaggeration=0.5, temperature=0.8, cfg_weight=0.5, min_p=0.05, top_p=1.0, repetition_penalty=1.2):
        """Generate speech from text using RunPod"""
        # Call RunPod endpoint for generation
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "tts",
                "text": text,
                "voice_id": self.current_voice_id,  # Use current voice if set
                "parameters": {
                    "exaggeration": exaggeration,
                    "temperature": temperature,
                    "cfg_weight": cfg_weight,
                    "min_p": min_p,
                    "top_p": top_p,
                    "repetition_penalty": repetition_penalty
                }
            }
        )
        
        # Convert base64 audio to numpy array
        audio_data = base64.b64decode(response["audio_data"])
        audio_array = np.frombuffer(audio_data, dtype=np.float32)
        return torch.from_numpy(audio_array).unsqueeze(0)

    def prepare_conditionals(self, wav_fpath: str, exaggeration=0.5):
        """Prepare voice clone conditionals using RunPod"""
        # Extract voice name from path
        voice_name = os.path.basename(os.path.dirname(wav_fpath))
        
        # Load and encode the audio file
        audio, _ = librosa.load(wav_fpath, sr=self.sr)
        audio_bytes = audio.tobytes()
        audio_b64 = base64.b64encode(audio_bytes).decode()
        
        # Call RunPod endpoint for voice cloning
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "clone",
                "reference_audio": audio_b64,
                "voice_name": voice_name,
                "parameters": {
                    "exaggeration": exaggeration
                }
            }
        )
        
        # Store voice ID for future use
        self.current_voice_id = response.get("voice_id")
        
        # Return None since actual conditionals are handled on RunPod
        return None 