"""Text-to-Speech generation page."""
import gradio as gr
from typing import Dict, Any, Tuple, List
from ...config import settings
from ...config.paths import PathManager

def create_tts_page(state: Dict[str, Any]) -> None:
    """Create the text-to-speech interface."""
    path_manager = PathManager()
    
    def get_available_voices() -> List[str]:
        """Get list of available voices including samples and clones."""
        voices = ["Default"]  # Always include default voice
        
        try:
            # Add voice samples
            samples_path = path_manager.get_voice_samples_path()
            if samples_path.exists():
                for sample_file in samples_path.glob("*.wav"):
                    voices.append(sample_file.stem)
            
            # Add voice clones
            clones_path = path_manager.get_voice_clones_path()
            if clones_path.exists():
                for clone_dir in clones_path.iterdir():
                    if clone_dir.is_dir() and (clone_dir / "config.json").exists():
                        voices.append(clone_dir.name)
            
            return sorted(list(set(voices)))  # Remove duplicates and sort
        except Exception as e:
            print(f"Error getting available voices: {e}")
            return ["Default"]
    
    with gr.Tab("Text-to-Speech"):
        gr.Markdown("""
        # 🗣️ Text-to-Speech
        Generate speech from text using your voice clones.
        """)
        
        with gr.Row():
            # Text Input
            with gr.Column():
                text_input = gr.Textbox(
                    label="Text to Speak",
                    placeholder="Enter the text you want to convert to speech",
                    lines=5
                )
                
                voice_name = gr.Dropdown(
                    label="Voice",
                    choices=get_available_voices(),
                    value="Default",
                    allow_custom_value=True
                )
                
                with gr.Row():
                    exaggeration = gr.Slider(
                        minimum=0.25,
                        maximum=2.0,
                        value=0.5,
                        step=0.05,
                        label="Voice Exaggeration"
                    )
                    
                    temperature = gr.Slider(
                        minimum=0.1,
                        maximum=1.0,
                        value=0.8,
                        step=0.05,
                        label="Temperature"
                    )
                    
                    cfg_weight = gr.Slider(
                        minimum=0.2,
                        maximum=1.0,
                        value=0.5,
                        step=0.05,
                        label="CFG Weight"
                    )
                
                with gr.Row():
                    min_p = gr.Slider(
                        minimum=0.0,
                        maximum=0.2,
                        value=0.05,
                        step=0.01,
                        label="Min P"
                    )
                    
                    top_p = gr.Slider(
                        minimum=0.5,
                        maximum=1.0,
                        value=1.0,
                        step=0.05,
                        label="Top P"
                    )
                    
                    repetition_penalty = gr.Slider(
                        minimum=1.0,
                        maximum=2.0,
                        value=1.2,
                        step=0.1,
                        label="Repetition Penalty"
                    )
                
                generate_btn = gr.Button("Generate Speech", variant="primary")
            
            # Audio Output
            with gr.Column():
                audio_output = gr.Audio(label="Generated Speech")
        
        # Event handlers
        def generate_speech(
            text: str,
            voice: str,
            exaggeration: float,
            temperature: float,
            cfg_weight: float,
            min_p: float,
            top_p: float,
            repetition_penalty: float
        ) -> str:
            """Generate speech from text."""
            if not text:
                return None
            
            try:
                print(f"Generating speech: text='{text}', voice='{voice}'")
                
                # Get the TTS engine from state
                tts_engine = state["model"].value
                if not tts_engine:
                    print("TTS engine not initialized")
                    raise RuntimeError("TTS engine not initialized")
                
                # Generate speech
                output_path = path_manager.get_voice_output_path() / f"{voice or 'default'}_output.wav"
                print(f"Generating speech to: {output_path}")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                result = tts_engine.generate_speech(
                    text=text,
                    voice_name=None if voice == "Default" else voice,
                    output_path=str(output_path),
                    exaggeration=exaggeration,
                    temperature=temperature,
                    cfg_weight=cfg_weight,
                    min_p=min_p,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty
                )
                
                if not output_path.exists():
                    raise RuntimeError("Failed to generate speech output")
                
                print(f"Successfully generated speech at: {output_path}")
                return str(output_path)
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Error generating speech: {error_details}")
                raise RuntimeError(f"Error generating speech: {str(e)}")
        
        # Connect UI components
        generate_btn.click(
            fn=generate_speech,
            inputs=[
                text_input,
                voice_name,
                exaggeration,
                temperature,
                cfg_weight,
                min_p,
                top_p,
                repetition_penalty
            ],
            outputs=audio_output
        ) 