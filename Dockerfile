FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-dev \
    build-essential \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Debug: Check Python version and pip location
RUN echo "=== Python and pip versions ===" && \
    python3 --version && \
    which python3 && \
    pip3 --version && \
    which pip3

# Set working directory
WORKDIR /app

# Create voice library structure
RUN mkdir -p /app/voice_library/{clones,output,samples}

# Copy only the necessary files
COPY pyproject.toml requirements.txt LICENSE README.md /app/
COPY src/ /app/src/
COPY runpod_deploy/handler.py /app/handler.py

# Debug: List contents
RUN echo "=== Contents of /app ===" && \
    ls -la /app && \
    echo "=== Contents of /app/src ===" && \
    ls -la /app/src

# Upgrade pip and install build tools
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Install runpod and other critical dependencies first
RUN pip3 install --no-cache-dir runpod==1.3.3 torch==2.4.1 torchaudio==2.4.1

# Install the package in development mode with verbose output
RUN pip3 install -e . -v

# Final verification of installation
RUN python3 -c "import runpod; print('RunPod version:', runpod.__version__)"

# Set the handler as the entrypoint
CMD ["python3", "/app/handler.py"] 