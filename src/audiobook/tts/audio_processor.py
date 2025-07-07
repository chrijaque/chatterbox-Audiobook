import numpy as np
import librosa
import soundfile as sf
from typing import List, Tuple, Optional
import wave
import os
from pathlib import Path

class AudioProcessor:
    def __init__(self, sample_rate: int = 24000, output_base_dir: str = "voice_library/output"):
        self.sample_rate = sample_rate
        self.output_base_dir = Path(output_base_dir)
        
        # Ensure output directories exist
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        (self.output_base_dir / "tts").mkdir(exist_ok=True)

    def save_audio_chunks(
        self,
        audio_chunks: List[np.ndarray],
        project_name: str,
        output_subdir: str = "tts"
    ) -> Tuple[List[str], str]:
        """Save audio chunks as numbered WAV files in the proper output directory"""
        if not project_name.strip():
            project_name = "untitled_audiobook"
        
        # Sanitize project name
        safe_project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_project_name = safe_project_name.replace(' ', '_')
        
        # Create output directory in the proper location
        project_dir = self.output_base_dir / output_subdir / safe_project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        for i, audio_chunk in enumerate(audio_chunks, 1):
            filename = f"{safe_project_name}_{i:03d}.wav"
            filepath = project_dir / filename
            
            # Save as WAV file
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                
                # Convert float32 to int16
                audio_int16 = (audio_chunk * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            saved_files.append(str(filepath))
        
        return saved_files, str(project_dir)

    def save_single_audio(
        self,
        audio_data: np.ndarray,
        filename: str,
        output_subdir: str = "tts"
    ) -> str:
        """Save a single audio file to the output directory"""
        # Ensure filename has .wav extension
        if not filename.endswith('.wav'):
            filename += '.wav'
        
        # Create output path
        output_path = self.output_base_dir / output_subdir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as WAV file
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            
            # Convert float32 to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wav_file.writeframes(audio_int16.tobytes())
        
        return str(output_path)

    def analyze_audio_level(self, audio_data: np.ndarray) -> dict:
        """Analyze audio levels"""
        rms = np.sqrt(np.mean(audio_data**2))
        db_rms = 20 * np.log10(rms) if rms > 0 else -100
        
        peak = np.max(np.abs(audio_data))
        db_peak = 20 * np.log10(peak) if peak > 0 else -100
        
        return {
            'rms': rms,
            'rms_db': db_rms,
            'peak': peak,
            'peak_db': db_peak
        }

    def normalize_audio(
        self,
        audio_data: np.ndarray,
        target_db: float = -18.0,
        method: str = 'rms'
    ) -> np.ndarray:
        """Normalize audio to target level"""
        levels = self.analyze_audio_level(audio_data)
        
        if method == 'rms':
            current_db = levels['rms_db']
        else:  # peak
            current_db = levels['peak_db']
        
        # Calculate gain needed
        gain_db = target_db - current_db
        gain_linear = 10 ** (gain_db / 20)
        
        # Apply gain
        normalized_audio = audio_data * gain_linear
        
        # Clip to prevent distortion
        normalized_audio = np.clip(normalized_audio, -1.0, 1.0)
        
        return normalized_audio

    def combine_audio_chunks(
        self,
        audio_chunks: List[np.ndarray],
        crossfade_duration: float = 0.1
    ) -> np.ndarray:
        """Combine audio chunks with optional crossfade"""
        if not audio_chunks:
            return np.array([])
        
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        
        crossfade_samples = int(crossfade_duration * self.sample_rate)
        
        # Initialize output array
        total_samples = sum(len(chunk) for chunk in audio_chunks)
        total_samples -= crossfade_samples * (len(audio_chunks) - 1)
        combined = np.zeros(total_samples)
        
        # First chunk (no fade in)
        pos = 0
        combined[pos:pos + len(audio_chunks[0]) - crossfade_samples] = \
            audio_chunks[0][:-crossfade_samples]
        pos += len(audio_chunks[0]) - crossfade_samples
        
        # Middle chunks (crossfade both ends)
        for chunk in audio_chunks[1:-1]:
            # Create fade curves
            fade_in = np.linspace(0, 1, crossfade_samples)
            fade_out = np.linspace(1, 0, crossfade_samples)
            
            # Apply crossfade
            combined[pos:pos + crossfade_samples] += \
                chunk[:crossfade_samples] * fade_in
            combined[pos + crossfade_samples:pos + len(chunk) - crossfade_samples] = \
                chunk[crossfade_samples:-crossfade_samples]
            pos += len(chunk) - crossfade_samples
        
        # Last chunk (no fade out)
        if len(audio_chunks) > 1:
            fade_in = np.linspace(0, 1, crossfade_samples)
            combined[pos:pos + crossfade_samples] += \
                audio_chunks[-1][:crossfade_samples] * fade_in
            combined[pos + crossfade_samples:] = \
                audio_chunks[-1][crossfade_samples:]
        
        return combined
