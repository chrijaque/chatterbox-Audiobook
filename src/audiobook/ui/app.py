"""Main application interface."""

import gradio as gr
from typing import Optional, List, Dict, Any, Tuple
from .styles import css
from .state import create_state_components
from .pages.tts import create_tts_page
from .pages.voice_library import create_voice_library_page
from ..tts.engine import TTSEngine
from ..config import settings
from ..config.paths import PathManager
from ..tts import AudiobookTTS

# Custom CSS for styling
css = """
.voice-library-header {
    text-align: center;
    margin-bottom: 2rem;
}
.voice-library-header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}
.voice-library-header p {
    font-size: 1.2rem;
    color: #666;
}
"""

def create_state_components() -> Dict[str, gr.State]:
    """Create state components for the application."""
    path_manager = PathManager()
    return {
        "model": gr.State(None),
        "voice_library_path": gr.State(str(path_manager.get_voice_library_path())),
        "voice_samples_path": gr.State(str(path_manager.get_voice_samples_path())),
        "voice_clones_path": gr.State(str(path_manager.get_voice_clones_path())),
        "voice_output_path": gr.State(str(path_manager.get_voice_output_path()))
    }

def create_app(model: Optional[TTSEngine] = None) -> gr.Blocks:
    """Create the main Gradio application interface."""
    
    # Initialize TTS engine if not provided
    if isinstance(model, AudiobookTTS):
        tts_engine = model
    else:
        # Check if RunPod is configured
        use_runpod = settings.is_runpod_configured
        if use_runpod:
            print("Initializing TTS engine with RunPod")
            print(f"RunPod API Key: {settings.RUNPOD_API_KEY[:8]}...")
            print(f"RunPod Endpoint ID: {settings.ENDPOINT_ID}")
        else:
            print("Warning: RunPod not configured, using local TTS engine")
        
        tts_engine = AudiobookTTS(use_runpod=use_runpod)
    
    with gr.Blocks(css=css, title="Chatterbox TTS") as app:
        # Create header
        gr.HTML("""
        <div class="voice-library-header">
            <h1>🎧 Chatterbox TTS</h1>
            <p>Voice cloning and text-to-speech system</p>
        </div>
        """)
        
        # Initialize state
        state_components = create_state_components()
        state_components["model"].value = tts_engine
        
        # Create tabs
        with gr.Tabs():
            # Voice Library tab (for creating and testing voice clones)
            create_voice_library_page(state_components)
            
            # Text-to-Speech tab (for testing voice generation)
            create_tts_page(state_components)
    
    return app

def launch_app(
    model: Optional[TTSEngine] = None,
    share: bool = False,
    server_port: Optional[int] = None,
    server_name: Optional[str] = None
) -> None:
    """Launch the Gradio application."""
    app = create_app(model)
    app.launch(
        share=share,
        server_port=server_port,
        server_name=server_name
    )

def create_ui(tts_engine: Optional[AudiobookTTS] = None) -> gr.Blocks:
    """Create the main application interface."""
    
    # Configure theme
    theme = gr.themes.Default(
        font=gr.themes.GoogleFont("Inter"),
        font_mono=gr.themes.GoogleFont("IBM Plex Mono")
    ).set(
        body_background_fill="*neutral_50",
        block_background_fill="*neutral_100",
        block_label_background_fill="*primary_100",
        block_title_text_color="*primary_500"
    )
    
    # Create app with theme
    app = gr.Blocks(
        theme=theme,
        css=css,
        title="Chatterbox TTS",
        analytics_enabled=False,  # Disable analytics to prevent postMessage errors
        mode="simple"  # Use simple mode to reduce asset dependencies
    )
    
    with app:
        # Create header
        gr.HTML("""
        <div class="voice-library-header">
            <h1>🎧 Chatterbox TTS</h1>
            <p>Voice cloning and text-to-speech system</p>
        </div>
        """)
        
        # Initialize state
        state_components = create_state_components()
        state_components["model"].value = tts_engine
        
        # Create tabs
        with gr.Tabs():
            # Voice Library tab (for creating and testing voice clones)
            create_voice_library_page(state_components)
            
            # Text-to-Speech tab (for testing voice generation)
            create_tts_page(state_components)
    
    return app

def launch_app(
    model: Optional[TTSEngine] = None,
    share: bool = False,
    server_port: Optional[int] = None,
    server_name: Optional[str] = None
) -> None:
    """Launch the Gradio application."""
    app = create_app(model)
    app.launch(
        share=share,
        server_port=server_port,
        server_name=server_name
    )

def create_ui(tts_engine: Optional[AudiobookTTS] = None) -> gr.Blocks:
    """Create the UI application.
    
    Args:
        tts_engine: Optional TTS engine instance. If not provided, a new one will be created.
    
    Returns:
        gr.Blocks: The Gradio application.
    """
    if tts_engine is None:
        # Check if RunPod is configured
        use_runpod = settings.is_runpod_configured
        if use_runpod:
            print("Initializing TTS engine with RunPod")
            print(f"RunPod API Key: {settings.RUNPOD_API_KEY[:8]}...")
            print(f"RunPod Endpoint ID: {settings.ENDPOINT_ID}")
        else:
            print("Warning: RunPod not configured, using local TTS engine")
        
        tts_engine = AudiobookTTS(use_runpod=use_runpod)
        
    with gr.Blocks(title="Chatterbox TTS") as app:
        gr.Markdown("# 🎙️ Chatterbox TTS")
        
        with gr.Tabs():
            # Text-to-Speech Tab
            with gr.TabItem("Text to Speech"):
                with gr.Row():
                    with gr.Column():
                        text_input = gr.Textbox(
                            label="Text to speak",
                            placeholder="Enter text here...",
                            lines=5
                        )
                        voice_name = gr.Dropdown(
                            label="Voice",
                            choices=["Default"],
                            value="Default",
                            interactive=True
                        )
                        
                        with gr.Row():
                            exaggeration = gr.Slider(
                                label="Exaggeration",
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
                                maximum=0.2,
                                value=0.05,
                                step=0.01
                            )
                        
                        with gr.Row():
                            top_p = gr.Slider(
                                label="Top P",
                                minimum=0.0,
                                maximum=1.0,
                                value=1.0,
                                step=0.1
                            )
                            repetition_penalty = gr.Slider(
                                label="Repetition Penalty",
                                minimum=1.0,
                                maximum=2.0,
                                value=1.2,
                                step=0.1
                            )
                        
                        generate_btn = gr.Button("Generate Speech", variant="primary")
                    
                    with gr.Column():
                        audio_output = gr.Audio(
                            label="Generated Speech",
                            type="numpy",
                            interactive=False
                        )
            
            # Voice Cloning Tab
            with gr.TabItem("Voice Cloning"):
                with gr.Tabs():
                    # Voice Samples Tab
                    with gr.TabItem("🎙️ Voice Samples"):
                        with gr.Row():
                            # Left Column - Sample Recording
                            with gr.Column():
                                gr.HTML("<h3>🎤 Record Voice Sample</h3>")
                                
                                # Voice Details
                                voice_name = gr.Textbox(
                                    label="Voice Name",
                                    placeholder="e.g., john_doe",
                                    info="Unique identifier for the voice"
                                )
                                voice_description = gr.Textbox(
                                    label="Description",
                                    placeholder="e.g., Male voice, American accent",
                                    lines=2
                                )
                                
                                # Audio Recording
                                sample_audio = gr.Audio(
                                    label="Voice Sample",
                                    sources=["microphone", "upload"],
                                    type="filepath"
                                )
                                
                                save_sample_btn = gr.Button(
                                    "💾 Save Voice Sample",
                                    variant="primary",
                                    size="lg"
                                )
                                sample_status = gr.HTML(
                                    "<div class='voice-status'>Ready to record voice sample</div>"
                                )
                            
                            # Right Column - Sample Management
                            with gr.Column():
                                gr.HTML("<h3>📚 Voice Samples</h3>")
                                samples_list = gr.Dataframe(
                                    headers=["Name", "Display Name", "Description", "Samples"],
                                    label="Available Voice Samples",
                                    interactive=True
                                )
                                with gr.Row():
                                    refresh_samples_btn = gr.Button("🔄 Refresh")
                                    delete_sample_btn = gr.Button("🗑️ Delete", variant="stop")
                    
                    # Voice Clones Tab
                    with gr.TabItem("🎭 Voice Clones"):
                        with gr.Row():
                            # Left Column - Clone Creation
                            with gr.Column():
                                gr.HTML("<h3>🔨 Create Voice Clone</h3>")
                                
                                # Sample Selection
                                sample_selector = gr.Dropdown(
                                    label="Voice Sample",
                                    choices=[],
                                    info="Select a voice sample to clone"
                                )
                                
                                # Clone Details
                                clone_name = gr.Textbox(
                                    label="Clone Name",
                                    placeholder="e.g., john_narrator",
                                    info="Unique identifier for the clone"
                                )
                                clone_description = gr.Textbox(
                                    label="Description",
                                    placeholder="e.g., Optimized for narration",
                                    lines=2
                                )
                                
                                # Voice Settings
                                with gr.Row():
                                    clone_exaggeration = gr.Slider(
                                        label="Exaggeration",
                                        minimum=0.0,
                                        maximum=1.0,
                                        value=0.5,
                                        step=0.1
                                    )
                                    clone_temperature = gr.Slider(
                                        label="Temperature",
                                        minimum=0.0,
                                        maximum=1.0,
                                        value=0.8,
                                        step=0.1
                                    )
                                
                                with gr.Row():
                                    clone_cfg_weight = gr.Slider(
                                        label="CFG Weight",
                                        minimum=0.0,
                                        maximum=1.0,
                                        value=0.5,
                                        step=0.1
                                    )
                                
                                create_clone_btn = gr.Button(
                                    "🎨 Create Voice Clone",
                                    variant="primary",
                                    size="lg"
                                )
                                clone_status = gr.HTML(
                                    "<div class='voice-status'>Ready to create voice clone</div>"
                                )
                            
                            # Right Column - Clone Management
                            with gr.Column():
                                gr.HTML("<h3>🎭 Voice Clones</h3>")
                                clones_list = gr.Dataframe(
                                    headers=["Name", "Display Name", "Description"],
                                    label="Available Voice Clones",
                                    interactive=True
                                )
                                with gr.Row():
                                    refresh_clones_btn = gr.Button("🔄 Refresh")
                                    delete_clone_btn = gr.Button("🗑️ Delete", variant="stop")
        
        # TTS Functions
        def generate_speech(
            text: str,
            voice_name: str,
            exaggeration: float,
            temperature: float,
            cfg_weight: float,
            min_p: float,
            top_p: float,
            repetition_penalty: float
        ):
            """Generate speech from text."""
            try:
                audio_data = tts_engine.generate_speech(
                    text=text,
                    voice_name=None if voice_name == "Default" else voice_name,
                    exaggeration=exaggeration,
                    temperature=temperature,
                    cfg_weight=cfg_weight,
                    min_p=min_p,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty
                )
                return audio_data
            except Exception as e:
                gr.Warning(f"Error generating speech: {str(e)}")
                return None

        # Voice Sample Functions
        def save_voice_sample(
            audio_path: str,
            name: str,
            description: str
        ) -> Tuple[str, List[List[str]]]:
            """Save a voice sample recording."""
            try:
                if not audio_path or not name:
                    return "❌ Audio file and name are required", []
                
                with open(audio_path, "rb") as f:
                    audio_data = f.read()
                
                voice_name = tts_engine.save_voice_sample(
                    audio_data=audio_data,
                    voice_name=name,
                    description=description
                )
                
                # Update samples list
                samples = tts_engine.list_voice_samples()
                samples_data = [
                    [s["name"], s["display_name"], s.get("description", ""), s["sample_count"]]
                    for s in samples
                ]
                
                return f"✅ Voice sample '{voice_name}' saved successfully!", samples_data
            except Exception as e:
                return f"❌ Error saving voice sample: {str(e)}", []

        def list_voice_samples() -> List[List[str]]:
            """List all available voice samples."""
            try:
                samples = tts_engine.list_voice_samples()
                return [
                    [s["name"], s["display_name"], s.get("description", ""), s["sample_count"]]
                    for s in samples
                ]
            except Exception as e:
                gr.Warning(f"Error listing voice samples: {str(e)}")
                return []

        def delete_voice_sample(samples_data: List[List[str]]) -> Tuple[str, List[List[str]], Dict[str, Any]]:
            """Delete a voice sample."""
            try:
                if not samples_data:
                    return "❌ No sample selected", [], gr.Dropdown(choices=[])
                
                sample_name = samples_data[0][0]  # First column of selected row
                
                if tts_engine.delete_voice_sample(sample_name):
                    samples = list_voice_samples()
                    sample_choices = update_sample_choices()
                    return f"✅ Voice sample '{sample_name}' deleted successfully!", samples, sample_choices
                else:
                    return f"❌ Failed to delete voice sample '{sample_name}'", [], gr.Dropdown(choices=[])
            except Exception as e:
                return f"❌ Error deleting voice sample: {str(e)}", [], gr.Dropdown(choices=[])

        # Voice Clone Functions
        def create_voice_clone(
            sample_name: str,
            clone_name: str,
            description: str,
            exaggeration: float,
            cfg_weight: float,
            temperature: float
        ) -> Tuple[str, List[List[str]]]:
            """Create a voice clone from a sample."""
            try:
                if not sample_name or not clone_name:
                    return "❌ Sample name and clone name are required", []
                
                # Get the latest sample audio
                samples = tts_engine.list_voice_samples()
                sample = next((s for s in samples if s["name"] == sample_name), None)
                if not sample:
                    return f"❌ Voice sample '{sample_name}' not found", []
                
                # Read the latest sample audio
                sample_dir = settings.VOICE_SAMPLES_PATH / sample_name
                latest_sample = sorted(sample_dir.glob("sample_*.wav"))[-1]
                with open(latest_sample, "rb") as f:
                    audio_data = f.read()
                
                # Create the clone
                voice_name = tts_engine.clone_voice(
                    audio_data=audio_data,
                    voice_name=clone_name,
                    description=description
                )
                
                # Update clones list
                clones = tts_engine.list_voice_clones()
                clones_data = [
                    [c["name"], c["display_name"], c.get("description", "")]
                    for c in clones
                ]
                
                return f"✅ Voice clone '{voice_name}' created successfully!", clones_data
            except Exception as e:
                return f"❌ Error creating voice clone: {str(e)}", []

        def list_voice_clones() -> List[List[str]]:
            """List all available voice clones."""
            try:
                clones = tts_engine.list_voice_clones()
                return [
                    [c["name"], c["display_name"], c.get("description", "")]
                    for c in clones
                ]
            except Exception as e:
                gr.Warning(f"Error listing voice clones: {str(e)}")
                return []

        def delete_voice_clone(clones_data: List[List[str]]) -> Tuple[str, List[List[str]]]:
            """Delete a voice clone."""
            try:
                if not clones_data:
                    return "❌ No clone selected", []
                
                clone_name = clones_data[0][0]  # First column of selected row
                
                if tts_engine.delete_voice_clone(clone_name):
                    clones = list_voice_clones()
                    return f"✅ Voice clone '{clone_name}' deleted successfully!", clones
                else:
                    return f"❌ Failed to delete voice clone '{clone_name}'", []
            except Exception as e:
                return f"❌ Error deleting voice clone: {str(e)}", []

        def update_sample_choices() -> Dict[str, Any]:
            """Update the sample selection dropdown."""
            try:
                samples = tts_engine.list_voice_samples()
                choices = [s["name"] for s in samples]
                return gr.Dropdown(choices=choices)
            except Exception as e:
                gr.Warning(f"Error updating sample choices: {str(e)}")
                return gr.Dropdown(choices=[])

        def update_voice_dropdown() -> Dict[str, Any]:
            """Update the voice dropdown with available voices."""
            try:
                clones = tts_engine.list_voice_clones()
                choices = ["Default"] + [c["name"] for c in clones]
                return gr.Dropdown(choices=choices)
            except Exception as e:
                gr.Warning(f"Error updating voices: {str(e)}")
                return gr.Dropdown(choices=["Default"])

        # Wire up event handlers
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

        save_sample_btn.click(
            fn=save_voice_sample,
            inputs=[
                sample_audio,
                voice_name,
                voice_description
            ],
            outputs=[sample_status, samples_list]
        ).success(
            fn=update_sample_choices,
            outputs=[sample_selector]
        )

        create_clone_btn.click(
            fn=create_voice_clone,
            inputs=[
                sample_selector,
                clone_name,
                clone_description,
                clone_exaggeration,
                clone_cfg_weight,
                clone_temperature
            ],
            outputs=[clone_status, clones_list]
        ).success(
            fn=update_voice_dropdown,
            outputs=[voice_name]
        )

        refresh_samples_btn.click(
            fn=list_voice_samples,
            outputs=[samples_list]
        ).success(
            fn=update_sample_choices,
            outputs=[sample_selector]
        )

        refresh_clones_btn.click(
            fn=list_voice_clones,
            outputs=[clones_list]
        ).success(
            fn=update_voice_dropdown,
            outputs=[voice_name]
        )

        delete_sample_btn.click(
            fn=delete_voice_sample,
            inputs=[samples_list],
            outputs=[sample_status, samples_list, sample_selector]
        )

        delete_clone_btn.click(
            fn=delete_voice_clone,
            inputs=[clones_list],
            outputs=[clone_status, clones_list]
        ).success(
            fn=update_voice_dropdown,
            outputs=[voice_name]
        )

        # Initialize lists
        samples_list.value = list_voice_samples()
        clones_list.value = list_voice_clones()
        sample_selector.choices = [s[0] for s in samples_list.value]
        voice_name.choices = ["Default"] + [c[0] for c in clones_list.value]
        
        return app 