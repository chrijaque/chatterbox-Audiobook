"""Text-to-Speech generation page."""
import gradio as gr
from typing import Dict, Any, Optional
from ...tts import AudiobookTTS

def create_tts_page(state: Dict[str, Any]) -> None:
    """Create the text-to-speech interface."""
    tts_engine: Optional[AudiobookTTS] = state.get("tts_engine")
    if not tts_engine:
        raise ValueError("TTS engine not provided in state")
    
    with gr.Column():
        text_input = gr.Textbox(
            label="Text to Speak",
            placeholder="Enter text to convert to speech...",
            lines=5
        )
        
        with gr.Row():
            voice_select = gr.Dropdown(
                label="Select Voice",
                choices=[],
                interactive=True
            )
            refresh_voices_btn = gr.Button("Refresh Voices")
        
        with gr.Row():
            exaggeration = gr.Slider(
                label="Emotion Exaggeration",
                minimum=0.0,
                maximum=1.0,
                value=0.5,
                step=0.1
            )
            temperature = gr.Slider(
                label="Temperature",
                minimum=0.1,
                maximum=1.0,
                value=0.8,
                step=0.1
            )
        
        with gr.Row():
            cfg_weight = gr.Slider(
                label="CFG Weight",
                minimum=0.0,
                maximum=1.0,
                value=0.5,
                step=0.1
            )
            min_p = gr.Slider(
                label="Min P",
                minimum=0.0,
                maximum=0.5,
                value=0.05,
                step=0.01
            )
        
        generate_btn = gr.Button("Generate Speech", variant="primary")
        audio_output = gr.Audio(label="Generated Speech")
        status = gr.Textbox(label="Status", interactive=False)
        
        # Event handlers
        def refresh_voices():
            """Refresh the voice list."""
            try:
                profiles = tts_engine.list_voice_profiles()
                return [p.name for p in profiles]
            except Exception as e:
                print(f"Error refreshing voices: {e}")
                return []
        
        def generate_speech(
            text: str,
            voice_name: str,
            exag: float,
            temp: float,
            cfg: float,
            min_p: float
        ):
            """Generate speech from text."""
            try:
                audio_data = tts_engine.generate_speech(
                    text,
                    voice_name,
                    exaggeration=exag,
                    temperature=temp,
                    cfg_weight=cfg,
                    min_p=min_p
                )
                return audio_data, "Speech generated successfully"
            except Exception as e:
                return None, f"Error generating speech: {str(e)}"
        
        # Wire up event handlers
        refresh_voices_btn.click(
            fn=refresh_voices,
            inputs=[],
            outputs=[voice_select]
        )
        
        generate_btn.click(
            fn=generate_speech,
            inputs=[
                text_input,
                voice_select,
                exaggeration,
                temperature,
                cfg_weight,
                min_p
            ],
            outputs=[audio_output, status]
        )
        
        # Initial voice list load
        voice_select.choices = refresh_voices() 