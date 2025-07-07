#!/bin/bash

# Build and deploy script for RunPod Docker image

set -e

# Configuration
IMAGE_NAME="chatterbox-audiobook"
TAG="latest"
REGISTRY="your-registry"  # Replace with your Docker registry

echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME:$TAG -f runpod_deploy/Dockerfile .

echo "📦 Tagging image for registry..."
docker tag $IMAGE_NAME:$TAG $REGISTRY/$IMAGE_NAME:$TAG

echo "🚀 Pushing to registry..."
docker push $REGISTRY/$IMAGE_NAME:$TAG

echo "✅ Build and deploy complete!"
echo "Image: $REGISTRY/$IMAGE_NAME:$TAG"
echo ""
echo "To use this image in RunPod:"
echo "1. Go to RunPod Templates"
echo "2. Create new template with image: $REGISTRY/$IMAGE_NAME:$TAG"
echo "3. Set container ports: 8000"
echo "4. Set environment variables as needed"
echo "5. Deploy endpoint using this template" 