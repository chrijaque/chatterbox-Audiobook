#!/bin/bash

# Local build script for testing the Docker image

set -e

IMAGE_NAME="chatterbox-audiobook"
TAG="latest"

echo "🔨 Building Docker image locally..."
docker build -t $IMAGE_NAME:$TAG -f runpod_deploy/Dockerfile .

echo "✅ Build complete!"
echo "Image: $IMAGE_NAME:$TAG"
echo ""
echo "To test locally:"
echo "docker run -p 8000:8000 -e RUNPOD_API_KEY=your_key $IMAGE_NAME:$TAG"
echo ""
echo "To save and upload to RunPod:"
echo "1. docker save $IMAGE_NAME:$TAG | gzip > chatterbox-audiobook.tar.gz"
echo "2. Upload to your preferred registry (Docker Hub, etc.)"
echo "3. Use the registry URL in RunPod template" 