#!/bin/bash

# Deploy script for RunPod using the root Dockerfile

set -e

# Configuration
IMAGE_NAME="chatterbox-audiobook"
TAG="latest"
DOCKER_USERNAME="${DOCKER_USERNAME:-your-docker-username}"

echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME:$TAG -f Dockerfile .

echo "📦 Tagging image for Docker Hub..."
docker tag $IMAGE_NAME:$TAG $DOCKER_USERNAME/$IMAGE_NAME:$TAG

echo "🚀 Pushing to Docker Hub..."
echo "Note: Make sure you're logged in with 'docker login'"
docker push $DOCKER_USERNAME/$IMAGE_NAME:$TAG

echo "✅ Deploy complete!"
echo ""
echo "🎯 RunPod Setup Instructions:"
echo "1. Go to RunPod Templates: https://www.runpod.io/console/serverless/user/templates"
echo "2. Click 'New Template'"
echo "3. Container Image: $DOCKER_USERNAME/$IMAGE_NAME:$TAG"
echo "4. Container Registry Credentials: (if private repo)"
echo "5. Environment Variables:"
echo "   - RUNPOD_API_KEY: (your RunPod API key)"
echo "   - VOICE_LIBRARY_PATH: /app/voice_library"
echo "6. Container Start Command: python3 /app/handler.py"
echo "7. Exposed HTTP Ports: 8000 (if using serverless API)"
echo "8. Container Disk: 10GB+"
echo "9. Save template and deploy endpoint"
echo ""
echo "🔗 Image URL for RunPod: $DOCKER_USERNAME/$IMAGE_NAME:$TAG" 