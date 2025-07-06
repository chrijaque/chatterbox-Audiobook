# RunPod Serverless Deployment for Chatterbox

This directory contains the necessary files for deploying Chatterbox as a serverless application on RunPod.

## Directory Structure
```
runpod_deploy/
├── Dockerfile
├── handler.py
├── requirements.txt
└── serverless_api.py
```

## Setup Instructions
1. Build the Docker image
2. Push to Docker Hub
3. Create RunPod serverless endpoint
4. Deploy FastAPI gateway 