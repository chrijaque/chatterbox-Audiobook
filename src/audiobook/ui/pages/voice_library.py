"""Voice library management interface."""
import gradio as gr
from typing import Dict, Any, List, Tuple, Optional
import os
import tempfile
import torchaudio
from ...voice_management import VoiceManager
from ...config import settings

class VoiceLibraryUI:
    def __init__(self, voice_manager: VoiceManager):
        self.voice_manager = voice_manager
        
    def create_ui(self) -> gr.Blocks:
        """Create the voice library interface."""
        with gr.Blocks() as interface:
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
                
                # Voice Cloning Tab
                with gr.Tab("Voice Cloning"):
                    gr.Markdown("### Voice Cloning")
                    gr.Markdown("Convert any audio to sound like a specific voice from your library")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("**Source Audio** (what to convert)")
                            source_audio = gr.Audio(
                                label="Upload Source Audio",
                                type="filepath"
                            )
                        
                        with gr.Column():
                            gr.Markdown("**Target Voice** (voice to mimic)")
                            target_voice_dropdown = gr.Dropdown(
                                label="Select Target Voice",
                                choices=[],
                                interactive=True
                            )
                            refresh_target_voices_btn = gr.Button("Refresh Voice List")
                    
                    with gr.Row():
                        output_name = gr.Textbox(
                            label="Output Name",
                            placeholder="Enter name for cloned audio..."
                        )
                    
                    perform_cloning_btn = gr.Button("Perform Voice Cloning", variant="primary")
                    cloning_status = gr.Textbox(label="Cloning Status", interactive=False)
                    cloned_audio_output = gr.Audio(label="Cloned Audio Output")
            
            # Event handlers
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
                """Clone a voice with specific parameters - saves voice profile with custom settings."""
                print(f"\nUI Clone Voice called with:")
                print(f"  audio_path: {audio_path}")
                print(f"  name: {name}")
                print(f"  description: {desc}")
                print(f"  parameters: exaggeration={exaggeration}, cfg_weight={cfg_weight}, temperature={temperature}")
                
                if not audio_path:
                    return "Please record or upload a voice sample", refresh_voices()
                if not name:
                    return "Please provide a name for the voice", refresh_voices()
                    
                try:
                    print(f"Saving voice profile for {name}...")
                    with open(audio_path, 'rb') as f:
                        audio_data = f.read()
                    
                    result = self.voice_manager.clone_voice(
                        voice_name=name,
                        audio_data=audio_data,
                        display_name=name,
                        description=desc,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight,
                        temperature=temperature
                    )
                    print(f"Voice profile saved successfully to clones directory")
                    return f"Voice '{name}' profile saved with custom parameters!", refresh_voices()
                except Exception as e:
                    print(f"Exception in clone_voice: {str(e)}")
                    return f"Error saving voice profile: {str(e)}", refresh_voices()
            
            def save_voice(audio_path: str, name: str, desc: str) -> Tuple[str, List[List[str]]]:
                """Save a voice sample."""
                if not audio_path:
                    return "Please record or upload a voice sample", refresh_voices()
                if not name:
                    return "Please provide a name for the voice", refresh_voices()
                    
                try:
                    with open(audio_path, 'rb') as f:
                        audio_data = f.read()
                    
                    result = self.voice_manager.save_sample(
                        voice_name=name,
                        audio_data=audio_data,
                        display_name=name,
                        description=desc
                    )
                    return f"Voice sample '{name}' saved successfully!", refresh_voices()
                except Exception as e:
                    return f"Error saving voice: {str(e)}", refresh_voices()
            
            def refresh_voices() -> List[List[str]]:
                """Refresh the voice list."""
                try:
                    profiles = self.voice_manager.get_profiles()
                    return [[p.voice_name, p.description or "", p.voice_type] for p in profiles]
                except Exception as e:
                    print(f"Error refreshing voices: {e}")
                    return []
            
            def delete_voice(selected_data: List[List[str]]) -> Tuple[str, List[List[str]]]:
                """Delete selected voice."""
                if not selected_data:
                    return "Please select a voice to delete", refresh_voices()
                try:
                    name = selected_data[0][0]  # First column is name
                    self.voice_manager.delete_profile(name)
                    return f"Voice '{name}' deleted successfully", refresh_voices()
                except Exception as e:
                    return f"Error deleting voice: {str(e)}", refresh_voices()
            
            def perform_voice_cloning(
                source_audio_path: str,
                target_voice_name: str,
                output_name: str
            ) -> Tuple[str, Optional[str]]:
                """Perform actual voice cloning using RunPod."""
                if not source_audio_path:
                    return "Please upload source audio", None
                if not target_voice_name:
                    return "Please select a target voice", None
                if not output_name:
                    return "Please provide an output name", None
                
                try:
                    from audiobook.voice_management import RUNPOD_AVAILABLE
                    if not RUNPOD_AVAILABLE:
                        return "Voice cloning not available - RunPod not configured", None
                    
                    print(f"Starting voice cloning via RunPod: {source_audio_path} -> {target_voice_name}")
                    
                    # Perform voice cloning using RunPod
                    cloned_audio_path = self.voice_manager.clone_voice_from_files(
                        source_audio_path=source_audio_path,
                        target_voice_name=target_voice_name,
                        output_name=output_name
                    )
                    
                    return f"Voice cloning completed successfully! Output saved to: {cloned_audio_path}", cloned_audio_path
                    
                except Exception as e:
                    print(f"Voice cloning error: {str(e)}")
                    return f"Voice cloning failed: {str(e)}", None
            
            def refresh_target_voices() -> List[str]:
                """Refresh the target voice dropdown."""
                try:
                    profiles = self.voice_manager.get_profiles()
                    return [p.voice_name for p in profiles]
                except Exception as e:
                    print(f"Error refreshing target voices: {e}")
                    return []
            
            # Connect event handlers
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
                fn=refresh_voices,
                inputs=[],
                outputs=[voice_list]
            )
            
            delete_btn.click(
                fn=delete_voice,
                inputs=[voice_list],
                outputs=[status, voice_list]
            )
            
            # Voice Cloning event handlers
            perform_cloning_btn.click(
                fn=perform_voice_cloning,
                inputs=[source_audio, target_voice_dropdown, output_name],
                outputs=[cloning_status, cloned_audio_output]
            )
            
            refresh_target_voices_btn.click(
                fn=refresh_target_voices,
                inputs=[],
                outputs=[target_voice_dropdown]
            )
            
            # Initial voice list load
            voice_list.value = refresh_voices()
            
            # Initial target voices load
            target_voice_dropdown.choices = refresh_target_voices()
        
        return interface
