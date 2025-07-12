"""
Audiobook TTS implementation using Chatterbox models via RunPod
"""
import runpod
import base64
import numpy as np
import librosa
import json
import torch
from pathlib import Path
from typing import Optional, Dict, Any, Union
from .config import settings
from .config.paths import PathManager

class AudiobookTTS:
    """Text-to-Speech engine using Chatterbox models via RunPod."""
    
    def __init__(self, device: str = "runpod"):
        """Initialize the TTS engine."""
        if not settings.is_runpod_configured:
            raise ValueError("RunPod API key not configured. Please set RUNPOD_API_KEY in settings.")
        
        if not settings.ENDPOINT_ID:
            raise ValueError("RunPod endpoint ID not configured")
            
        runpod.api_key = settings.RUNPOD_API_KEY
        self.endpoint = runpod.Endpoint(settings.ENDPOINT_ID)
        self.path_manager = PathManager()
        self.sample_rate = 24000  # Standard sample rate for Chatterbox
        self.sr = self.sample_rate  # Alias for compatibility
        self.device = device  # For compatibility with models.py
    
    @classmethod
    def from_pretrained(cls, device: str = "runpod") -> 'AudiobookTTS':
        """Create AudiobookTTS instance (for compatibility with models.py interface)."""
        return cls(device=device)
    
    def generate(
        self,
        text: str,
        audio_prompt_path: Optional[str] = None,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        **kwargs
    ) -> torch.Tensor:
        """Generate speech from text (for compatibility with models.py interface).
        
        Args:
            text: Text to convert to speech
            audio_prompt_path: Path to audio prompt file (voice sample)
            exaggeration: Voice exaggeration factor (0.25-2.0)
            temperature: Generation temperature (0.1-1.0)
            cfg_weight: CFG weight (0.2-1.0)
            **kwargs: Additional arguments (ignored for compatibility)
            
        Returns:
            torch.Tensor: Generated audio as tensor
        """
        # For RunPod-based generation, we need a voice to use
        # If audio_prompt_path is provided, extract voice name from it
        voice_name = None
        if audio_prompt_path:
            # Try to extract voice name from path or use a default
            voice_path = Path(audio_prompt_path)
            voice_name = voice_path.parent.name if voice_path.parent.name != "." else voice_path.stem
        
        # Generate audio using RunPod
        audio_path = self.generate_speech(
            text=text,
            voice_name=voice_name,
            exaggeration=exaggeration,
            temperature=temperature,
            cfg_weight=cfg_weight
        )
        
        # Load the generated audio and return as tensor
        audio, _ = librosa.load(audio_path, sr=self.sample_rate)
        return torch.from_numpy(audio).unsqueeze(0)
    
    def generate_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
    ) -> str:
        """Generate speech from text using specified voice.
        
        Args:
            text: Text to convert to speech
            voice_name: Name of voice to use (None for default)
            output_path: Path to save audio file (None for auto-generated)
            exaggeration: Voice exaggeration factor (0.25-2.0)
            temperature: Generation temperature (0.1-1.0)
            cfg_weight: CFG weight (0.2-1.0)
            
        Returns:
            Path to generated audio file
        """
        try:
            # Load voice configuration if specified
            voice_id = None
            if voice_name:
                voice_path = self.path_manager.get_voice_clones_path() / voice_name
                config_path = voice_path / "config.json"
                if not config_path.exists():
                    raise FileNotFoundError(f"Voice not found: {voice_name}")
                
                with open(config_path, "r") as f:
                    voice_config = json.load(f)
                    voice_id = voice_config.get("voice_id")
                
                # If no voice ID, we need to clone the voice first
                if not voice_id:
                    voice_id = self._clone_voice(voice_path / "original.wav", exaggeration)
                    # Save the voice ID back to config
                    voice_config["voice_id"] = voice_id
                    with open(config_path, "w") as f:
                        json.dump(voice_config, f, indent=2)
            
            # Generate output path if not specified
            if output_path is None:
                output_path = self.path_manager.get_tts_output_path() / f"{voice_name or 'default'}_output.wav"
            elif isinstance(output_path, str):
                output_path = Path(output_path)
                
            # Ensure output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate speech using RunPod
            audio_data = self._generate_speech(
                text=text,
                voice_id=voice_id,
                exaggeration=exaggeration,
                temperature=temperature,
                cfg_weight=cfg_weight,
            )
            
            # Save audio to file
            import soundfile as sf
            sf.write(str(output_path), audio_data, self.sample_rate)
            
            return str(output_path)
            
        except Exception as e:
            import traceback
            print(f"Error generating speech: {traceback.format_exc()}")
            raise
    
    def _clone_voice(self, voice_path: Path, exaggeration: float = 0.5) -> str:
        """Clone a voice from an audio file using Chatterbox models via RunPod.
        
        Args:
            voice_path: Path to voice audio file
            exaggeration: Voice exaggeration factor
            
        Returns:
            Voice ID for the cloned voice
        """
        # Load and encode the audio file
        audio, _ = librosa.load(str(voice_path), sr=self.sample_rate)
        audio_bytes = audio.tobytes()
        audio_b64 = base64.b64encode(audio_bytes).decode()
        
        # Call RunPod endpoint for voice cloning
        response = self.endpoint.run({
            "type": "clone",
            "reference_audio": audio_b64,
            "voice_name": voice_path.parent.name,
            "parameters": {
                "exaggeration": exaggeration
            }
        })
        
        result = response.output()
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"RunPod error: {result['error']}")
        
        voice_id = result.get("voice_id") if isinstance(result, dict) else None
        if not voice_id:
            raise ValueError("No voice ID returned from RunPod")
        
        return voice_id
    
    def _generate_speech(
        self,
        text: str,
        voice_id: Optional[str],
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
    ) -> np.ndarray:
        """Generate speech using Chatterbox models via RunPod."""
        # Call RunPod endpoint for generation
        response = self.endpoint.run({
            "type": "tts",
            "text": text,
            "voice_id": voice_id,
            "parameters": {
                "exaggeration": exaggeration,
                "temperature": temperature,
                "cfg_weight": cfg_weight
            }
        })
        
        result = response.output()
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"RunPod error: {result['error']}")
        
        # Convert base64 audio to numpy array
        if not isinstance(result, dict) or "audio_data" not in result:
            raise ValueError("Invalid response format from RunPod")
        
        audio_data = base64.b64decode(result["audio_data"])
        return np.frombuffer(audio_data, dtype=np.float32) 