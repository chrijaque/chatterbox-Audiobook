"""Application launcher module."""

import argparse
import uvicorn
from typing import Optional
from pathlib import Path
from .ui.app import create_ui
from .api.endpoints import create_api
from .tts import AudiobookTTS
from .config.settings import RUNPOD_API_KEY, ENDPOINT_ID  # Import directly from settings
import gradio as gr

def launch_app(
    mode: str = "ui",
    host: Optional[str] = None,
    port: Optional[int] = None,
    use_runpod: Optional[bool] = None,
    **kwargs
):
    """Launch the Chatterbox application in either UI or API mode.
    
    Args:
        mode: Either "ui" or "api"
        host: Host to bind to (overrides environment variable)
        port: Port to bind to (overrides environment variable)
        use_runpod: Whether to use RunPod for inference (overrides settings)
        **kwargs: Additional keyword arguments passed to the app
    """
    # Create voice library directories
    voice_library = Path("voice_library")
    (voice_library / "samples").mkdir(parents=True, exist_ok=True)
    (voice_library / "clones").mkdir(parents=True, exist_ok=True)
    (voice_library / "output").mkdir(parents=True, exist_ok=True)
    
    # Use provided host/port or fall back to settings
    host = host or "127.0.0.1"
    port = port or 7860
    
    # Check RunPod configuration
    if use_runpod is None:
        use_runpod = bool(RUNPOD_API_KEY and ENDPOINT_ID)
    
    if use_runpod:
        if not (RUNPOD_API_KEY and ENDPOINT_ID):
            raise ValueError("RunPod not configured. Please check your .env file has RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID set.")
        print("Initializing TTS engine with RunPod")
        if RUNPOD_API_KEY:
            print(f"RunPod API Key: {RUNPOD_API_KEY[:8]}...")
        if ENDPOINT_ID:
            print(f"RunPod Endpoint ID: {ENDPOINT_ID}")
    else:
        print("Using local TTS engine")
    
    # Initialize TTS engine with RunPod configuration
    tts_engine = AudiobookTTS()
    if use_runpod and RUNPOD_API_KEY and ENDPOINT_ID:
        print("Enabling RunPod for TTS engine")
        tts_engine.use_runpod = True
        if hasattr(tts_engine, 'endpoint_id'):
            tts_engine.endpoint_id = ENDPOINT_ID
    
    if mode == "ui":
        # Create UI with improved configuration
        app = create_ui(tts_engine)
        app.launch(
            server_name=host,
            server_port=port,
            share=kwargs.get('share', False),
            show_error=True,
            quiet=False,
            favicon_path=None
        )
    elif mode == "api":
        app = create_api(tts_engine=tts_engine)
        uvicorn.run(
            app,
            host=host,
            port=port,
            **kwargs
        )
    else:
        raise ValueError(f"Invalid mode: {mode}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Launch Chatterbox TTS")
    parser.add_argument("--mode", choices=["ui", "api"], default="ui", help="Launch mode")
    parser.add_argument("--host", help="Host to bind to")
    parser.add_argument("--port", type=int, help="Port to bind to")
    parser.add_argument("--share", action="store_true", help="Enable sharing")
    parser.add_argument("--use-runpod", action="store_true", help="Use RunPod for inference")
    
    args = parser.parse_args()
    
    launch_app(
        mode=args.mode,
        host=args.host,
        port=args.port,
        share=args.share,
        use_runpod=args.use_runpod
    )

if __name__ == "__main__":
    main() 