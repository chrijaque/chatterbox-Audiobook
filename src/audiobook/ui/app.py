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
    voice_manager = VoiceManager(voice_library_path=settings.VOICE_LIBRARY_PATH)
    
    with gr.Blocks(css=css, title="Chatterbox TTS") as app:
        gr.HTML("""
            <div class="header">
                <h1>Chatterbox TTS</h1>
                <p>Text-to-Speech with Voice Cloning</p>
            </div>
        """)
        
        with gr.Tabs() as tabs:
            # Voice Library Tab - Use dedicated VoiceLibraryUI
            with gr.Tab("Voice Library"):
                # Create the voice library interface content directly
                gr.Markdown("# Voice Library")
                
                with gr.Tabs():
                    # Voice Recording/Upload Tab
                    with gr.Tab("Voice Library"):
                    gr.Markdown("### Record or Upload Voice")
                        
                    with gr.Row():
                            # Record Voice Section
                        with gr.Column():
                            audio_recorder = gr.Audio(
                                label="Record Voice",
                                type="filepath"
                            )
                            
                            # Upload Voice Section
                        with gr.Column():
                            audio_uploader = gr.Audio(
                                label="Upload Voice File",
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
                    
                        # Voice Parameters
                    with gr.Row():
                        exaggeration = gr.Slider(
                                minimum=0, maximum=1, value=0.5,
                                label="Exaggeration"
                        )
                        cfg_weight = gr.Slider(
                                minimum=0, maximum=1, value=0.5,
                                label="CFG Weight"
                        )
                        temperature = gr.Slider(
                                minimum=0, maximum=1, value=0.8,
                                label="Temperature"
                        )
                    
                    with gr.Row():
                        clone_btn = gr.Button("Clone Voice", variant="primary")
                        save_btn = gr.Button("Save Voice Sample")
                        
                        status = gr.Textbox(label="Status", interactive=False)
                    
                        # Voice List Section
                    gr.Markdown("### Available Voices")
                    voice_list = gr.Dataframe(
                            headers=["Name", "Description", "Type"],
                            label="Voice Library"
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
        
        # Voice Library Event Handlers
        def clone_voice_wrapper(
            recorder_audio: str,
            uploader_audio: str,
            name: str,
            desc: str,
            exaggeration: float,
            cfg_weight: float,
            temperature: float
        ) -> Tuple[str, List[List[str]]]:
            """Wrapper to handle both recorder and uploader audio inputs."""
            # Use recorder audio if available, otherwise use uploader audio
            audio_path = recorder_audio if recorder_audio else uploader_audio
            return clone_voice(audio_path, name, desc, exaggeration, cfg_weight, temperature)
        
        def save_voice_wrapper(
            recorder_audio: str,
            uploader_audio: str,
            name: str,
            desc: str
        ) -> Tuple[str, List[List[str]]]:
            """Wrapper to handle both recorder and uploader audio inputs."""
            # Use recorder audio if available, otherwise use uploader audio
            audio_path = recorder_audio if recorder_audio else uploader_audio
            return save_voice(audio_path, name, desc)
        
        def clone_voice(
            audio_path: str,
            name: str,
            desc: str,
            exaggeration: float,
            cfg_weight: float,
            temperature: float
        ) -> Tuple[str, List[List[str]]]:
            """Clone voice: save sample in 'samples' folder + send to RunPod + save clone in 'clones' folder."""
            if not audio_path:
                return "Please record or upload a voice sample", refresh_voice_list()
            if not name:
                return "Please provide a name for the voice", refresh_voice_list()
                
            try:
                # Check if RunPod is available
                from audiobook.voice_management import RUNPOD_AVAILABLE
                if not RUNPOD_AVAILABLE:
                    return "Voice cloning not available - RunPod not configured", refresh_voice_list()
                
                print(f"Starting voice cloning process for: {name}")
                
                # Step 1: Save the voice sample in "samples" folder
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
                
                voice_name = voice_manager.save_sample(
                    voice_name=name,
                    audio_data=audio_data,
                    display_name=name,
                    description=desc
                )
                print(f"✅ Voice sample saved in samples folder: {voice_name}")
                
                # Step 2: Send to RunPod for voice cloning
                from audiobook.api.runpod_client import RunPodClient
                client = RunPodClient(
                    api_key=settings.RUNPOD_API_KEY,
                    endpoint_id=settings.ENDPOINT_ID
                )
                
                parameters = {
                    "exaggeration": exaggeration,
                    "cfg_weight": cfg_weight,
                    "temperature": temperature
                }
                
                print(f"📤 Sending audio to RunPod for voice cloning...")
                result = client.clone_voice(
                    audio_path=audio_path,
                    voice_name=name,
                    display_name=name,
                    description=desc,
                    parameters=parameters
                )
                
                if not result.is_success:
                    return f"Voice cloning failed: {result.message}", refresh_voice_list()
                
                print(f"✅ RunPod voice cloning completed successfully!")
                
                # Step 3: Save cloned voice info in "clones" folder
                cloned_voice_name = voice_manager.clone_voice(
                    voice_name=f"{name}_cloned",
                    audio_data=audio_data,
                    display_name=f"{name} (Cloned)",
                    description=f"Cloned version of {desc}",
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature
                )
                print(f"✅ Cloned voice saved in clones folder: {cloned_voice_name}")
                
                return f"🎉 Voice cloning completed! Original saved in 'samples', clone saved in 'clones'. Voice '{voice_name}' is ready for TTS!", refresh_voice_list()
                
            except Exception as e:
                print(f"❌ Voice cloning error: {str(e)}")
                import traceback
                traceback.print_exc()
                return f"Error during voice cloning: {str(e)}", refresh_voice_list()
        
        def save_voice(audio_path: str, name: str, desc: str) -> Tuple[str, List[List[str]]]:
            """Save a voice sample."""
            if not audio_path:
                return "Please record or upload a voice sample", refresh_voice_list()
            if not name:
                return "Please provide a name for the voice", refresh_voice_list()
                
            try:
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
                
                # voice_manager.save_sample() returns a string (the voice name), not a tuple
                voice_name = voice_manager.save_sample(
                    voice_name=name,
                    audio_data=audio_data,
                    display_name=name,
                    description=desc
                )
                return f"Voice sample '{voice_name}' saved successfully!", refresh_voice_list()
            except Exception as e:
                return f"Error saving voice: {str(e)}", refresh_voice_list()
        
        def refresh_voice_list() -> List[List[str]]:
            """Refresh the voice list."""
            try:
                profiles = voice_manager.get_profiles()
                return [[p.voice_name, p.description or "", p.voice_type] for p in profiles]
            except Exception as e:
                print(f"Error refreshing voices: {e}")
                return []
        
        def delete_voice(selected_data: List[List[str]]) -> Tuple[str, List[List[str]]]:
            """Delete selected voice."""
            if not selected_data:
                return "Please select a voice to delete", refresh_voice_list()
            try:
                name = selected_data[0][0]  # First column is name
                voice_manager.delete_profile(name)
                return f"Voice '{name}' deleted successfully", refresh_voice_list()
            except Exception as e:
                return f"Error deleting voice: {str(e)}", refresh_voice_list()
        

        
        # TTS Event Handlers
        def refresh_voices():
            """Refresh the voice list for TTS."""
            try:
                profiles = voice_manager.get_profiles()
                voice_names = [p.voice_name for p in profiles]
                return gr.update(choices=voice_names)
            except Exception as e:
                print(f"Error refreshing voices: {e}")
                import traceback
                traceback.print_exc()
                return gr.update(choices=[])
        
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
        
        # Connect TTS event handlers
        refresh_voices_btn.click(
            fn=refresh_voices,
            inputs=[],
            outputs=[voice_select]
        )
        
        generate_btn.click(
            fn=generate_speech,
            inputs=[text_input, voice_select],
            outputs=[tts_status, audio_output]
        )
        
        # Connect Voice Library event handlers
        clone_btn.click(
            fn=clone_voice_wrapper,
            inputs=[
                audio_recorder,
                audio_uploader,
                voice_name,
                voice_desc,
                exaggeration,
                cfg_weight,
                temperature
            ],
            outputs=[status, voice_list]
        )
        
        save_btn.click(
            fn=save_voice_wrapper,
            inputs=[
                audio_recorder,
                audio_uploader,
                voice_name,
                voice_desc
            ],
            outputs=[status, voice_list]
        )
        
        refresh_btn.click(
            fn=refresh_voice_list,
            inputs=[],
            outputs=[voice_list]
        )
        
        delete_btn.click(
            fn=delete_voice,
            inputs=[voice_list],
            outputs=[status, voice_list]
        )
        

        
        # Initial voice list load for TTS
        try:
            profiles = voice_manager.get_profiles()
            voice_names = [p.voice_name for p in profiles]
            voice_select.choices = voice_names
        except Exception as e:
            print(f"Error loading initial voices: {e}")
            voice_select.choices = []
        
        # Initial voice list load for Voice Library
        voice_list.value = refresh_voice_list()
        
        return app 