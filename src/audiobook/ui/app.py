"""Main application interface."""

import gradio as gr
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, List, Any

# Add src directory to path for imports
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from audiobook.tts import AudiobookTTS
from audiobook.voice_management import VoiceManager
from audiobook.config import settings
from .styles import css

# Global job state for cancellation
current_job_state = {
    "is_running": False,
    "task_id": None,
    "should_cancel": False
}

def create_ui(tts_engine: Optional[AudiobookTTS] = None) -> gr.Blocks:
    """Create the Gradio interface for the audiobook TTS application."""
    
    # Initialize voice manager
    voice_manager = VoiceManager(voice_library_path=settings.VOICE_LIBRARY_PATH)
    
    with gr.Blocks(css=css, title="Chatterbox TTS") as app:
        gr.HTML("""
            <div class="header">
                <h1>Chatterbox TTS</h1>
                <p>Text-to-Speech with Voice Cloning</p>
            </div>
        """)
        
        # State variables for job management
        job_state = gr.State(value={"is_running": False, "task_id": None, "should_cancel": False})
        
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
                            stop_btn = gr.Button("⏹️ Stop Cloning", variant="stop", visible=False)
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
            temperature: float,
            state: dict
        ) -> Tuple[str, List[List[str]], dict, bool, bool]:
            """Wrapper to handle both recorder and uploader audio inputs."""
            # Use recorder audio if available, otherwise use uploader audio
            audio_path = recorder_audio if recorder_audio else uploader_audio
            result, voice_list, updated_state = clone_voice(audio_path, name, desc, exaggeration, cfg_weight, temperature, state)
            
            # Return: status, voice_list, updated_state, clone_btn_visible, stop_btn_visible
            return result, voice_list, updated_state, not updated_state["is_running"], updated_state["is_running"]
        
        def stop_cloning(state: dict) -> Tuple[str, dict, bool, bool]:
            """Stop the current voice cloning job."""
            state["should_cancel"] = True
            
            # If we have a task_id, try to cancel it on RunPod
            if state.get("task_id"):
                try:
                    from audiobook.api.runpod_client import RunPodClient
                    client = RunPodClient(
                        api_key=settings.RUNPOD_API_KEY,
                        endpoint_id=settings.ENDPOINT_ID
                    )
                    client.cancel_job(state["task_id"])
                    print(f"🛑 Cancellation request sent for job: {state['task_id']}")
                except Exception as e:
                    print(f"Error cancelling job: {e}")
            
            state["is_running"] = False
            state["task_id"] = None
            
            # Return: status, updated_state, clone_btn_visible, stop_btn_visible
            return "🛑 Voice cloning cancelled by user", state, True, False
        
        def clone_voice(
            audio_path: str,
            name: str,
            desc: str,
            exaggeration: float,
            cfg_weight: float,
            temperature: float,
            state: dict
        ) -> Tuple[str, List[List[str]], dict]:
            """Clone voice: save sample in 'samples' folder + send to RunPod + save clone in 'clones' folder."""
            if not audio_path:
                return "Please record or upload a voice sample", refresh_voice_list(), state
            if not name:
                return "Please provide a name for the voice", refresh_voice_list(), state
            
            # Reset cancellation flag and set running state
            state["should_cancel"] = False
            state["is_running"] = True
            state["task_id"] = None
                
            try:
                # Check if RunPod is available
                from audiobook.voice_management import RUNPOD_AVAILABLE
                if not RUNPOD_AVAILABLE:
                    state["is_running"] = False
                    return "Voice cloning not available - RunPod not configured", refresh_voice_list(), state
                
                print(f"Starting voice cloning process for: {name}")
                
                # Check for cancellation
                if state["should_cancel"]:
                    state["is_running"] = False
                    return "🛑 Voice cloning cancelled by user", refresh_voice_list(), state
                
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
                
                # Check for cancellation
                if state["should_cancel"]:
                    state["is_running"] = False
                    return "🛑 Voice cloning cancelled by user", refresh_voice_list(), state
                
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
                
                # Submit job and get task_id for cancellation
                result, task_id = client.clone_voice_async(
                    audio_path=audio_path,
                    voice_name=name,
                    display_name=name,
                    description=desc,
                    parameters=parameters
                )
                
                if task_id:
                    state["task_id"] = task_id
                    print(f"📋 Job submitted with ID: {task_id}")
                    
                    # Poll for completion with cancellation checks
                    result = client.wait_for_completion(task_id, state)
                
                if not result.is_success:
                    state["is_running"] = False
                    if "cancelled" in result.message.lower():
                        return f"🛑 Voice cloning cancelled: {result.message}", refresh_voice_list(), state
                    return f"Voice cloning failed: {result.message}", refresh_voice_list(), state
                
                # Check for cancellation one more time
                if state["should_cancel"]:
                    state["is_running"] = False
                    return "🛑 Voice cloning cancelled by user", refresh_voice_list(), state
                
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
                
                state["is_running"] = False
                state["task_id"] = None
                return f"🎉 Voice cloning completed! Original saved in 'samples', clone saved in 'clones'. Voice '{voice_name}' is ready for TTS!", refresh_voice_list(), state
                
            except Exception as e:
                print(f"❌ Voice cloning error: {str(e)}")
                import traceback
                traceback.print_exc()
                state["is_running"] = False
                state["task_id"] = None
                return f"Error during voice cloning: {str(e)}", refresh_voice_list(), state
        
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
                temperature,
                job_state
            ],
            outputs=[status, voice_list, job_state, clone_btn, stop_btn]
        )
        
        stop_btn.click(
            fn=stop_cloning,
            inputs=[job_state],
            outputs=[status, job_state, clone_btn, stop_btn]
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