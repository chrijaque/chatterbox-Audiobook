"""
ChatterboxTTS - RunPod Client Implementation
This version uses RunPod for TTS generation and voice cloning
"""
import runpod
import base64
import numpy as np
import torch
import librosa

# RunPod configuration
RUNPOD_API_KEY = "***REMOVED***"
ENDPOINT_ID = "ekfmpp6tfjgc4v"
runpod.api_key = RUNPOD_API_KEY

class ChatterboxTTS:
    """Text-to-Speech interface using RunPod backend"""
    
    def __init__(self, device="cpu"):
        self.device = device
        self.sr = 24000  # sample rate of synthesized audio

    @classmethod
    def from_pretrained(cls, device="cpu") -> 'ChatterboxTTS':
        """Factory method to create TTS instance"""
        return cls(device=device)

    def generate(self, text, conds=None, exaggeration=0.5, temperature=0.8, cfg_weight=0.5, min_p=0.05, top_p=1.0, repetition_penalty=1.2):
        """Generate speech from text using RunPod"""
        # Call RunPod endpoint for generation
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "tts",
                "text": text,
                "voice_name": None,  # Using default voice for now
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

    def prepare_conditionals(self, wav_fpath, exaggeration=0.5):
        """Prepare voice clone conditionals using RunPod"""
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
                "voice_name": "temp_voice",  # Temporary voice name
                "parameters": {
                    "exaggeration": exaggeration
                }
            }
        )
        
        # Return None since actual conditionals are handled on RunPod
        return None