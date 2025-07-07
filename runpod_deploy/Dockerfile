FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn8-runtime

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY runpod_deploy/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code structure
COPY src/ src/
COPY runpod_deploy/handler.py .
COPY runpod_deploy/serverless_api.py .

# Copy configuration files
COPY .env .env

# Create necessary directories
RUN mkdir -p voice_library/samples voice_library/clones voice_library/output
RUN mkdir -p audiobook_projects

# Set environment variables
ENV PYTHONPATH=/app
ENV VOICE_LIBRARY_PATH=/app/voice_library

# Expose port for serverless API
EXPOSE 8000

# Run the handler
CMD ["python", "handler.py"] 