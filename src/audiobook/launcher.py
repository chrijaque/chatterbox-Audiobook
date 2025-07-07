"""Launcher module for the audiobook application."""

import os
import sys
import warnings
import uvicorn
import gradio as gr
from multiprocessing import Process
from audiobook.voice_management import VoiceManager
from audiobook.api.runpod_client import RunPodClient
from audiobook.tts.engine import TTSEngine
from audiobook.ui.app import create_ui
from audiobook.tts import AudiobookTTS
from dotenv import load_dotenv

# Filter deprecation warning from perth package
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

def launch_api_server(
    host: str = "localhost",
    port: int = 8000,
    reload: bool = True
):
    """Launch the FastAPI server."""
    # Detach from parent process stdin
    if os.name != 'nt':  # Not on Windows
        try:
            sys.stdin = open('/dev/null')
        except:
            pass  # Ignore if /dev/null is not available
    
    uvicorn.run(
        "audiobook.api.endpoints:app",
        host=host,
        port=port,
        reload=reload,
        reload_includes=['*.py'],  # Only watch Python files
        reload_excludes=['.*', '*.pyc', '__pycache__'],  # Exclude cache files
        log_level="info"
    )

def launch_ui(
    runpod_api_key: str,
    runpod_endpoint_id: str,
    voice_library_path: str = "voice_library",
    share: bool = False,
    server_name: str = "localhost",
    server_port: int = 7860,
):
    """Launch the Gradio UI for voice cloning and TTS"""
    
    # Initialize components
    runpod_client = RunPodClient(runpod_api_key, runpod_endpoint_id)
    tts_engine = AudiobookTTS(use_runpod=True)
    
    # Create and launch UI
    app = create_ui(tts_engine)
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        show_error=True  # Show detailed error messages
    )

def launch_development_servers(
    api_host: str = "localhost",
    api_port: int = 8000,
    ui_host: str = "localhost",
    ui_port: int = 7860,
):
    """Launch both API and UI servers for development."""
    
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    # Get RunPod credentials from environment
    api_key, endpoint_id = check_runpod_config()
    
    # Add src directory to Python path
    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    print("\nStarting development servers...")
    print(f"Added {src_dir} to PYTHONPATH")
    print(f"RunPod API Key: {'*' * 8}{api_key[-8:]}")
    print(f"RunPod Endpoint ID: {endpoint_id}")
    
    # Start API server in a separate process
    print("\nStarting API server...")
    api_process = Process(
        target=launch_api_server,
        args=(api_host, api_port, True)
    )
    api_process.start()
    
    # Start UI server in main process
    print("\nStarting UI server...")
    try:
        launch_ui(
            api_key,
            endpoint_id,
            server_name=ui_host,
            server_port=ui_port
        )
    except Exception as e:
        print(f"\nError starting UI server: {str(e)}")
        api_process.terminate()
        api_process.join()
        raise
    
    print("\nDevelopment servers running:")
    print(f"  API: http://{api_host}:{api_port}")
    print(f"  UI:  http://{ui_host}:{ui_port}")
    print("\nPress Ctrl+C to stop")
    
    try:
        api_process.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        api_process.terminate()
        api_process.join()
        sys.exit(0)

def check_runpod_config():
    """Check if RunPod is properly configured"""
    api_key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    
    if not api_key or not endpoint_id:
        print("\nRunPod Configuration Status:")
        print(f"RUNPOD_API_KEY: {'Set' if api_key else 'Not Set'}")
        print(f"RUNPOD_ENDPOINT_ID: {endpoint_id if endpoint_id else 'Not Set'}")
        print("\nPlease set the following environment variables:")
        print("export RUNPOD_API_KEY=your_api_key_here")
        print("export RUNPOD_ENDPOINT_ID=your_endpoint_id_here")
        raise ValueError("Missing RunPod configuration. Please set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID environment variables.")
    
    print("\nRunPod Configuration:")
    print(f"API Key: {'*' * len(api_key)}")
    print(f"RunPod Endpoint ID: {endpoint_id}")
    return api_key, endpoint_id

if __name__ == "__main__":
    launch_development_servers()
