# Video Frames Skill - Dockerfile
# Cell 0 OS - Video Analysis via FFmpeg

# Multi-stage build for optimized image size

# =============================================================================
# Base Image with FFmpeg
# =============================================================================
FROM jrottenberg/ffmpeg:5.1-ubuntu2004 AS base

LABEL maintainer="Cell 0 OS"
LABEL description="Video Frames Skill - FFmpeg-based video processing"

# Install Python and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3-pip \
    python3.9-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.9 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Install Python packages
RUN pip install --no-cache-dir \
    numpy>=1.20.0 \
    pillow>=9.0.0 \
    opencv-python-headless>=4.5.0 \
    pytest>=7.0.0 \
    pytest-asyncio>=0.20.0

# Set working directory
WORKDIR /app

# =============================================================================
# GPU-enabled variant (NVIDIA CUDA)
# =============================================================================
FROM nvidia/cuda:11.8.0-runtime-ubuntu20.04 AS gpu-base

LABEL maintainer="Cell 0 OS"
LABEL description="Video Frames Skill - GPU-accelerated FFmpeg video processing"

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install FFmpeg with NVIDIA support
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:jonathonf/ffmpeg-4 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    ffmpeg \
    python3.9 \
    python3-pip \
    python3.9-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.9 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Install Python packages
RUN pip install --no-cache-dir \
    numpy>=1.20.0 \
    pillow>=9.0.0 \
    opencv-python-headless>=4.5.0 \
    pytest>=7.0.0 \
    pytest-asyncio>=0.20.0

# Set working directory
WORKDIR /app

# =============================================================================
# Development Image
# =============================================================================
FROM base AS development

# Install development tools
RUN pip install --no-cache-dir \
    black \
    flake8 \
    mypy \
    pytest-cov \
    ipython \
    jupyter

# Copy skill files
COPY . /app/skills/video-frames/

ENV PYTHONPATH="/app:${PYTHONPATH}"

CMD ["python", "-c", "from skills.video_frames import VideoProcessor; print('Video Frames Skill loaded successfully')"]

# =============================================================================
# Production Image (CPU only)
# =============================================================================
FROM base AS production

# Copy skill files
COPY skills/video-frames/ /app/skills/video-frames/
COPY tests/ /app/tests/

ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV VIDEO_FRAMES_GPU_ENABLED="false"

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD ffmpeg -version || exit 1

CMD ["python", "-m", "pytest", "/app/tests/test_skill_video_frames.py", "-v", "--tb=short"]

# =============================================================================
# Production Image (GPU)
# =============================================================================
FROM gpu-base AS production-gpu

# Copy skill files
COPY skills/video-frames/ /app/skills/video-frames/
COPY tests/ /app/tests/

ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV VIDEO_FRAMES_GPU_ENABLED="true"
ENV NVIDIA_VISIBLE_DEVICES=all

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD ffmpeg -version || exit 1

CMD ["python", "-m", "pytest", "/app/tests/test_skill_video_frames.py", "-v", "--tb=short"]
