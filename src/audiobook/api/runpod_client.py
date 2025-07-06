import base64
import runpod
from typing import Optional
from pathlib import Path
from ..config import settings

class RunPodClient:
    def __init__(self):
        if not settings.is_runpod_configured:
            raise ValueError("RunPod API key and endpoint ID must be configured in environment variables")
        runpod.api_key = settings.RUNPOD_API_KEY
        self.endpoint_id = settings.RUNPOD_ENDPOINT_ID

    async def generate_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        min_p: float = 0.05,
        top_p: float = 1.0,
        repetition_penalty: float = 1.2
    ) -> bytes:
        """Generate speech using RunPod serverless endpoint"""
        response = runpod.run(
            endpoint_id=self.endpoint_id,
            input={
                "type": "tts",
                "text": text,
                "voice_name": voice_name,
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

        if "error" in response:
            raise RuntimeError(response["error"])

        return base64.b64decode(response["audio_data"])

    async def clone_voice(self, voice_name: str, audio_data: bytes) -> dict:
        """Clone a voice using RunPod serverless endpoint"""
        audio_base64 = base64.b64encode(audio_data).decode()
        
        response = runpod.run(
            endpoint_id=self.endpoint_id,
            input={
                "type": "clone",
                "reference_audio": audio_base64,
                "voice_name": voice_name
            }
        )

        if "error" in response:
            raise RuntimeError(response["error"])

        return response 