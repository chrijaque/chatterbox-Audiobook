"""State management for the UI application."""

import gradio as gr
from ..config.paths import PathManager

def create_state_components():
    """Create state components for the application."""
    path_manager = PathManager()
    return {
        "model": gr.State(None),
        "voice_library_path": gr.State(str(path_manager.get_voice_library_path())),
        "voice_samples_path": gr.State(str(path_manager.get_voice_samples_path())),
        "voice_clones_path": gr.State(str(path_manager.get_voice_clones_path())),
        "voice_output_path": gr.State(str(path_manager.get_voice_output_path()))
    }
