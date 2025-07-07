# RunPod Serverless Deployment for Chatterbox

This directory contains the necessary files for deploying Chatterbox as a serverless application on RunPod.

## Directory Structure
```
runpod_deploy/
├── Dockerfile
├── handler.py
├── requirements.txt
├── serverless_api.py
└── build.sh
```

## Setup Instructions

### 1. Build and Push Docker Image
The application requires building for the AMD64 architecture to run on RunPod servers. Use the provided build script:

```bash
# Make build script executable if needed
chmod +x build.sh

# Build and push the image
./build.sh
```

This will:
- Enable Docker buildx for multi-platform support
- Build the image for linux/amd64 platform
- Push to Docker Hub as chrijaque/chatterbox-runpod:latest

### 2. Create RunPod Serverless Endpoint
1. Go to RunPod serverless dashboard
2. Create new endpoint
3. Select the pushed image: chrijaque/chatterbox-runpod:latest
4. Configure environment variables:
   - RUNPOD_API_KEY
   - RUNPOD_ENDPOINT_ID
   - Other required environment variables

### 3. Deploy FastAPI Gateway
The FastAPI gateway provides a REST API interface to the RunPod endpoint:

```bash
python serverless_api.py
```

## Troubleshooting

### Common Issues

1. Architecture Mismatch
If you see the error "no matching manifest for linux/amd64", ensure:
- You're using the build script which handles multi-platform builds
- Docker buildx is properly configured
- The image was successfully pushed to Docker Hub

2. CUDA Compatibility
The image uses CUDA 11.8.0. Ensure your RunPod instance supports this version. 