#!/bin/bash

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements if needed
if [ ! -f "venv/.requirements_installed" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
    touch venv/.requirements_installed
fi

# Check for RunPod credentials
if [ -z "$RUNPOD_API_KEY" ] || [ -z "$RUNPOD_ENDPOINT_ID" ]; then
    echo "Error: Please set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID environment variables"
    echo "Example:"
    echo "export RUNPOD_API_KEY=your_api_key"
    echo "export RUNPOD_ENDPOINT_ID=your_endpoint_id"
    exit 1
fi

# Launch the UI
echo "Launching test UI..."
python -m src.audiobook.launcher 