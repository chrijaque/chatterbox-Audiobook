#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Add src directory to PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$SCRIPT_DIR/src"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Install python-dotenv if not already installed
pip install python-dotenv >/dev/null 2>&1

# Launch the application with proper environment loading
python - << EOF
import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join("${SCRIPT_DIR}", ".env")
if os.path.exists(env_path):
    print("Loading environment from .env file")
    load_dotenv(env_path)
    
    # Verify environment variables
    api_key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("ENDPOINT_ID")
    print(f"RunPod API Key: {'*' * 8}{api_key[-8:] if api_key else 'Not Set'}")
    print(f"Endpoint ID: {endpoint_id if endpoint_id else 'Not Set'}")

# Export environment variables to shell environment
if os.getenv("RUNPOD_API_KEY"):
    print("export RUNPOD_API_KEY=" + os.getenv("RUNPOD_API_KEY"))
if os.getenv("ENDPOINT_ID"):
    print("export ENDPOINT_ID=" + os.getenv("ENDPOINT_ID"))
EOF

# Evaluate the exports from Python
eval "$(python - << EOF
import os
from dotenv import load_dotenv
env_path = os.path.join("${SCRIPT_DIR}", ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    if os.getenv("RUNPOD_API_KEY"):
        print("export RUNPOD_API_KEY=" + os.getenv("RUNPOD_API_KEY"))
    if os.getenv("ENDPOINT_ID"):
        print("export ENDPOINT_ID=" + os.getenv("ENDPOINT_ID"))
EOF
)"

# Launch the application
python -m audiobook.launcher 