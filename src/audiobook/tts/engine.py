from typing import List, Tuple, Optional
import numpy as np
from chatterbox import ChatterboxTTS

class TTSEngine:
    def __init__(self, device: str = "cuda"):
        self.device = device
        self.model = None
        self.sample_rate = 24000

    def load_model(self):
        """Load the TTS model"""
        if self.model is None:
            self.model = ChatterboxTTS.from_pretrained(self.device)
        return self.model

    def generate_with_retry(
        self,
        text: str,
        audio_prompt_path: str,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        max_retries: int = 3
    ) -> Tuple[np.ndarray, str]:
        """Generate audio with automatic retry and CPU fallback"""
        for attempt in range(max_retries):
            try:
                if attempt > 0 and self.device == "cuda":
                    # Try CPU on subsequent attempts
                    self.model = ChatterboxTTS.from_pretrained("cpu")
                    self.device = "cpu"
                
                wav = self.model.generate(
                    text,
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=exaggeration,
                    temperature=temperature,
                    cfg_weight=cfg_weight,
                )
                return wav.squeeze(0).numpy(), self.device
                
            except RuntimeError as e:
                if attempt == max_retries - 1:
                    raise
                if "CUDA" in str(e) or "out of memory" in str(e).lower():
                    if self.device == "cuda":
                        self.model = None  # Force reload on next attempt
                        continue
                raise

    def process_text_chunks(
        self,
        chunks: List[str],
        audio_prompt_path: str,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5
    ) -> List[np.ndarray]:
        """Process a list of text chunks and return audio for each"""
        audio_chunks = []
        
        for chunk in chunks:
            wav, _ = self.generate_with_retry(
                chunk,
                audio_prompt_path,
                exaggeration,
                temperature,
                cfg_weight
            )
            audio_chunks.append(wav)
            
        return audio_chunks

    def generate_tts(
        self,
        text: str,
        audio_prompt_path: str,
        chunk_size: int = 50,
        exaggeration: float = 0.5,
        temperature: float = 0.8,
        cfg_weight: float = 0.5
    ) -> List[np.ndarray]:
        """Generate TTS for text, automatically handling chunking"""
        from .text_processor import chunk_text_by_sentences
        
        # Ensure model is loaded
        self.load_model()
        
        # Split text into chunks
        chunks = chunk_text_by_sentences(text, max_words=chunk_size)
        
        # Generate audio for each chunk
        return self.process_text_chunks(
            chunks,
            audio_prompt_path,
            exaggeration,
            temperature,
            cfg_weight
        )
