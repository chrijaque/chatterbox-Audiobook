"""Reusable UI components for the audiobook application."""

import gradio as gr
from typing import List, Tuple, Optional
from ..config import settings

def create_voice_selector(
    choices: List[Tuple[str, str]], 
    label: str = "Choose Voice",
    value: Optional[str] = None
) -> gr.Dropdown:
    """Create a voice selection dropdown with consistent styling."""
    return gr.Dropdown(
        choices=choices,
        label=label,
        value=value,
        info="Select a saved voice profile or use manual input"
    )

def create_audio_input(
    label: str = "Reference Audio",
    visible: bool = True
) -> gr.Audio:
    """Create an audio input component with consistent styling."""
    return gr.Audio(
        type="filepath",
        label=label,
        value=None,
        visible=visible
    )

def create_text_input(
    label: str = "Text Content",
    placeholder: str = "",
    lines: int = 3
) -> gr.Textbox:
    """Create a text input component with consistent styling."""
    return gr.Textbox(
        label=label,
        placeholder=placeholder,
        lines=lines,
        max_lines=20
    )

def create_status_html(message: str, style: str = "voice-status") -> gr.HTML:
    """Create a status display with consistent styling."""
    return gr.HTML(f'<div class="{style}">{message}</div>')

def create_voice_settings_group() -> Tuple[gr.Slider, gr.Slider, gr.Slider]:
    """Create a group of voice settings sliders."""
    with gr.Row():
        exaggeration = gr.Slider(
            0.25, 2, step=.05,
            label="Exaggeration (Neutral = 0.5)",
            value=0.5
        )
        cfg_weight = gr.Slider(
            0.2, 1, step=.05,
            label="CFG/Pace",
            value=0.5
        )
        temperature = gr.Slider(
            0.05, 5, step=.05,
            label="Temperature",
            value=0.8
        )
    return exaggeration, cfg_weight, temperature

def create_project_selector(
    choices: List[str],
    label: str = "Select Project"
) -> Tuple[gr.Dropdown, gr.Button, gr.Button]:
    """Create a project selection group with dropdown and buttons."""
    dropdown = gr.Dropdown(
        choices=choices,
        label=label,
        value=None,
        info="Choose from your existing audiobook projects"
    )
    
    with gr.Row():
        load_btn = gr.Button(
            "📂 Load Project",
            variant="secondary",
            size="lg"
        )
        refresh_btn = gr.Button(
            "🔄 Refresh",
            size="sm"
        )
    
    return dropdown, load_btn, refresh_btn

def create_audio_player(
    label: str,
    enable_trimming: bool = True
) -> gr.Audio:
    """Create an audio player component with consistent styling."""
    return gr.Audio(
        label=label,
        interactive=enable_trimming,
        show_download_button=True,
        show_share_button=False,
        show_controls=True,
        show_waveform=True,
        waveform_color="#01C6FF",
        waveform_progress_color="#0066B4",
        trim_region_color="#FF6B6B",
        show_recording_waveform=True,
        skip_length=5,
        sample_rate=settings.SAMPLE_RATE
    )

def create_header(title: str, subtitle: str) -> gr.HTML:
    """Create a header with consistent styling."""
    return gr.HTML(f"""
    <div class="audiobook-header">
        <h2>{title}</h2>
        <p>{subtitle}</p>
    </div>
    """) 