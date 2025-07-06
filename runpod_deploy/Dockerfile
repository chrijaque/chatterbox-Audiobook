FROM --platform=linux/amd64 nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install RunPod handler
RUN pip3 install --no-cache-dir runpod torch torchaudio --extra-index-url https://download.pytorch.org/whl/cu118

# Clone and install Chatterbox
RUN git clone https://github.com/chrijaque/chatterbox-Audiobook.git && \
    cd chatterbox-Audiobook && \
    pip3 install .

# Copy handler code
COPY handler.py .

# RunPod handler entrypoint
CMD [ "python3", "-u", "handler.py" ] 