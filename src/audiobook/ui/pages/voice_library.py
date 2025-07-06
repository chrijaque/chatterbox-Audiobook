"""Voice library management interface."""
import gradio as gr
from typing import Dict, Any, List, Tuple
import os
import tempfile
import torchaudio
from ...voice_management import VoiceManager
from ...config import settings

class VoiceLibraryUI:
    def __init__(self, voice_manager: VoiceManager):
        self.voice_manager = voice_manager
        
    def create_ui(self) -> None:
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
                                sources=["microphone"],
                                type="filepath"
                            )
                        
                        # Upload Voice Section
                        with gr.Column():
                            audio_uploader = gr.Audio(
                                label="Upload Voice File",
                                sources=["upload"],
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
                    
                    save_btn = gr.Button("Save Voice Sample", variant="primary")
                    save_status = gr.Textbox(label="Status", interactive=False)
                    
                    # Voice List Section
                    gr.Markdown("### Available Voices")
                    voice_list = gr.Dataframe(
                        headers=["Name", "Description", "Created"],
                        label="Voice Samples"
                    )
                    with gr.Row():
                        refresh_btn = gr.Button("Refresh List")
                        delete_btn = gr.Button("Delete Selected", variant="stop")
            
            # Event handlers
            def save_voice(audio_path: str, name: str, desc: str) -> Tuple[str, List[List[str]]]:
                """Save a voice sample."""
                if not audio_path:
                    return "Please record or upload a voice sample", refresh_voices()
                if not name:
                    return "Please provide a name for the voice", refresh_voices()
                    
                try:
                    result = self.voice_manager.save_voice_profile(
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
                    profiles = self.voice_manager.get_voice_profiles()
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
                    self.voice_manager.delete_voice_profile(name)
                    return f"Voice '{name}' deleted successfully", refresh_voices()
                except Exception as e:
                    return f"Error deleting voice: {str(e)}", refresh_voices()
            
            # Connect event handlers
            save_btn.click(
                fn=save_voice,
                inputs=[
                    audio_recorder,  # Try recorder first
                    voice_name,
                    voice_desc
                ],
                outputs=[save_status, voice_list]
            ).then(  # If recorder is empty, try uploader
                fn=save_voice,
                inputs=[
                    audio_uploader,
                    voice_name,
                    voice_desc
                ],
                outputs=[save_status, voice_list]
            )
            
            refresh_btn.click(
                fn=refresh_voices,
                inputs=[],
                outputs=[voice_list]
            )
            
            delete_btn.click(
                fn=delete_voice,
                inputs=[voice_list],
                outputs=[save_status, voice_list]
            )
            
            # Initial voice list load
            voice_list.value = refresh_voices()
            
        return interface
