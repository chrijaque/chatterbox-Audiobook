# Use an older NVIDIA PyTorch image that matches RunPod's drivers
FROM nvcr.io/nvidia/pytorch:23.12-py3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create necessary directories
RUN mkdir -p voice_library/samples voice_library/clones voice_library/output
RUN mkdir -p audiobook_projects

# Set environment variables
ENV PYTHONPATH=/app
ENV VOICE_LIBRARY_PATH=/app/voice_library

# Expose port for serverless API
EXPOSE 8000

# Run the handler
CMD ["python", "-m", "runpod_deploy.handler"] 