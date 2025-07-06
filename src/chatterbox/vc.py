"""
ChatterboxVC - RunPod Client Implementation
This version uses RunPod for voice cloning
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

class ChatterboxVC:
    """Voice cloning interface using RunPod backend"""
    
    def __init__(self, device="cpu"):
        self.device = device
        self.sr = 24000  # sample rate
        self.ref_dict = None

    @classmethod
    def from_pretrained(cls, device="cpu") -> 'ChatterboxVC':
        """Factory method to create voice cloning instance"""
        return cls(device=device)

    def set_target_voice(self, wav_fpath):
        """Set target voice for cloning using RunPod"""
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
                "voice_name": "temp_voice"  # Temporary voice name
            }
        )
        
        # Store voice ID for future use
        self.ref_dict = {"voice_id": response.get("voice_id")}

    def generate(self, audio, target_voice_path=None):
        """Generate speech in target voice using RunPod"""
        if target_voice_path:
            self.set_target_voice(target_voice_path)
        else:
            assert self.ref_dict is not None, "Please call set_target_voice first or specify target_voice_path"

        # Load and encode the input audio
        audio_data, _ = librosa.load(audio, sr=self.sr)
        audio_bytes = audio_data.tobytes()
        audio_b64 = base64.b64encode(audio_bytes).decode()
        
        # Call RunPod endpoint for voice conversion
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "convert",
                "audio": audio_b64,
                "voice_id": self.ref_dict["voice_id"]
            }
        )
        
        # Convert response to audio
        audio_data = base64.b64decode(response["audio_data"])
        audio_array = np.frombuffer(audio_data, dtype=np.float32)
        return torch.from_numpy(audio_array).unsqueeze(0)
