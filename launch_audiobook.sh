#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    set -a  # automatically export all variables
    source .env
    set +a
else
    echo "Warning: .env file not found"
fi

# Set environment variables for better output
export PYTHONUNBUFFERED=1
export GRADIO_SERVER_NAME="127.0.0.1"
export GRADIO_SERVER_PORT=7860

# Run the application
echo "🚀 Starting Chatterbox TTS..."
echo "📍 Server will be available at http://127.0.0.1:7860"
python -m src.audiobook.launcher --mode ui --host "$GRADIO_SERVER_NAME" --port "$GRADIO_SERVER_PORT" --use-runpod 