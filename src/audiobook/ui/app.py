"""Main application interface."""

import gradio as gr
from typing import Optional, List, Dict, Any, Tuple
from ..tts import AudiobookTTS
from ..config import settings
from ..voice_management import VoiceManager
from .styles import css

def create_ui(tts_engine: Optional[AudiobookTTS] = None) -> gr.Blocks:
    """Create the UI application."""
    if tts_engine is None:
        use_runpod = settings.is_runpod_configured
        if use_runpod:
            print("Initializing TTS engine with RunPod")
            print(f"RunPod API Key: {settings.RUNPOD_API_KEY[:8]}...")
            print(f"RunPod Endpoint ID: {settings.ENDPOINT_ID}")
        else:
            print("Warning: RunPod not configured, using local TTS engine")
        tts_engine = AudiobookTTS(use_runpod=use_runpod)
    
    # Initialize managers
    voice_manager = VoiceManager()
    
    with gr.Blocks(css=css, title="Chatterbox TTS") as app:
        gr.HTML("""
            <div class="header">
                <h1>Chatterbox TTS</h1>
                <p>Text-to-Speech with Voice Cloning</p>
            </div>
        """)
        
        with gr.Tabs() as tabs:
            # Voice Library Tab
            with gr.Tab("Voice Library"):
                # Voice Recording Section
                with gr.Column():
                    gr.Markdown("### Record or Upload Voice")
                    with gr.Row():
                        with gr.Column():
                            audio_recorder = gr.Audio(
                                label="Record Voice",
                                source="microphone",
                                type="filepath"
                            )
                        with gr.Column():
                            audio_uploader = gr.Audio(
                                label="Upload Voice File",
                                source="upload",
                                type="filepath"
                            )
                    
                    with gr.Row():
                        voice_name = gr.Textbox(
                            label="Voice Name",
                            placeholder="Enter a name for this voice..."
                        )
                        voice_desc = gr.Textbox(
                            label="Description",
                            placeholder="Describe the voice characteristics..."
                        )
                    
                    # Voice Cloning Parameters
                    with gr.Row():
                        exaggeration = gr.Slider(
                            label="Exaggeration",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.5,
                            step=0.1
                        )
                        cfg_weight = gr.Slider(
                            label="CFG Weight",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.5,
                            step=0.1
                        )
                        temperature = gr.Slider(
                            label="Temperature",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.8,
                            step=0.1
                        )
                    
                    with gr.Row():
                        clone_btn = gr.Button("Clone Voice", variant="primary")
                        save_btn = gr.Button("Save Voice Sample")
                    status_output = gr.Textbox(label="Status", interactive=False)
                    
                    # Voice List
                    gr.Markdown("### Available Voices")
                    voice_list = gr.Dataframe(
                        headers=["Name", "Description", "Created"],
                        label="Voice Samples"
                    )
                    with gr.Row():
                        refresh_btn = gr.Button("Refresh List")
                        delete_btn = gr.Button("Delete Selected", variant="stop")
            
            # TTS Tab
            with gr.Tab("Text-to-Speech"):
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
                    
                    generate_btn = gr.Button("Generate Speech", variant="primary")
                    audio_output = gr.Audio(label="Generated Speech")
                    tts_status = gr.Textbox(label="Status", interactive=False)
        
        # Event Handlers
        def clone_voice(audio_path: str, name: str, desc: str, exag: float, cfg: float, temp: float) -> Tuple[str, List[List[str]]]:
            """Handle voice cloning."""
            if not audio_path:
                return "Please provide a voice sample", refresh_voices()
            if not name:
                return "Please provide a name for the voice", refresh_voices()
                
            try:
                # Clone the voice
                parameters = {
                    "exaggeration": exag,
                    "cfg_weight": cfg,
                    "temperature": temp
                }
                result = voice_manager.clone_voice(
                    audio_path,
                    name,
                    description=desc,
                    parameters=parameters
                )
                return f"Voice cloned successfully!", refresh_voices()
            except Exception as e:
                return f"Error cloning voice: {str(e)}", refresh_voices()
        
        def save_voice(audio_path: str, name: str, desc: str) -> Tuple[str, List[List[str]]]:
            """Save a voice sample."""
            if not audio_path:
                return "Please record or upload a voice sample", refresh_voices()
            if not name:
                return "Please provide a name for the voice", refresh_voices()
                
            try:
                result = voice_manager.save_voice_profile(
                    name=name,
                    display_name=name,
                    description=desc,
                    audio_file=audio_path
                )
                return result, refresh_voices()
            except Exception as e:
                return f"Error saving voice: {str(e)}", refresh_voices()
        
        def refresh_voices() -> List[List[str]]:
            """Refresh the voice list."""
            try:
                profiles = voice_manager.get_voice_profiles()
                choices = [p.name for p in profiles]
                voice_select.choices = choices
                return [[p.name, p.description or "", p.created_date] for p in profiles]
            except Exception as e:
                print(f"Error refreshing voices: {e}")
                return []
        
        def delete_voice(selected_data: List[List[str]]) -> Tuple[str, List[List[str]]]:
            """Delete selected voice."""
            if not selected_data:
                return "Please select a voice to delete", refresh_voices()
            try:
                name = selected_data[0][0]  # First column is name
                voice_manager.delete_voice_profile(name)
                return f"Voice '{name}' deleted successfully", refresh_voices()
            except Exception as e:
                return f"Error deleting voice: {str(e)}", refresh_voices()
        
        def generate_speech(text: str, voice_name: str) -> Tuple[str, Optional[str]]:
            """Generate speech from text."""
            if not text:
                return "Please enter some text", None
            if not voice_name:
                return "Please select a voice", None
            
            try:
                audio_path = tts_engine.generate_speech(text, voice_name)
                return "Speech generated successfully!", audio_path
            except Exception as e:
                return f"Error generating speech: {str(e)}", None
        
        # Connect event handlers
        clone_btn.click(
            fn=clone_voice,
            inputs=[
                audio_recorder,
                voice_name,
                voice_desc,
                exaggeration,
                cfg_weight,
                temperature
            ],
            outputs=[status_output, voice_list]
        ).then(  # If recorder is empty, try uploader
            fn=clone_voice,
            inputs=[
                audio_uploader,
                voice_name,
                voice_desc,
                exaggeration,
                cfg_weight,
                temperature
            ],
            outputs=[status_output, voice_list]
        )
        
        save_btn.click(
            fn=save_voice,
            inputs=[
                audio_recorder,
                voice_name,
                voice_desc
            ],
            outputs=[status_output, voice_list]
        ).then(
            fn=save_voice,
            inputs=[
                audio_uploader,
                voice_name,
                voice_desc
            ],
            outputs=[status_output, voice_list]
        )
        
        refresh_btn.click(
            fn=refresh_voices,
            inputs=[],
            outputs=[voice_list]
        )
        
        refresh_voices_btn.click(
            fn=refresh_voices,
            inputs=[],
            outputs=[voice_list]
        )
        
        delete_btn.click(
            fn=delete_voice,
            inputs=[voice_list],
            outputs=[status_output, voice_list]
        )
        
        generate_btn.click(
            fn=generate_speech,
            inputs=[text_input, voice_select],
            outputs=[tts_status, audio_output]
        )
        
        # Initial voice list load
        voice_list.value = refresh_voices()
        
        return app 