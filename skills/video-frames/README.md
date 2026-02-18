# Video Frames Skill

Advanced video processing and analysis skill for Cell 0 OS, powered by FFmpeg with GPU acceleration support.

## Features

- ✅ **Frame Extraction** - Extract frames at specified FPS, time ranges, or scene-based
- ✅ **Audio Extraction** - Extract audio to MP3, WAV, AAC, FLAC, and more
- ✅ **Scene Detection** - Automatic scene change detection with configurable threshold
- ✅ **Video Summarization** - Generate key frame summaries using scene detection
- ✅ **Thumbnail Generation** - Create thumbnails at any timestamp
- ✅ **Format Conversion** - Convert between video formats with optional GPU acceleration
- ✅ **Clip Extraction** - Extract video segments with or without re-encoding
- ✅ **Metadata Extraction** - Comprehensive video metadata (duration, codecs, bitrate, etc.)
- ✅ **Batch Processing** - Process multiple videos efficiently
- ✅ **GPU Acceleration** - CUDA, Intel QSV, and AMD VAAPI support
- ✅ **Docker Support** - Containerized deployment with optional GPU runtime

## Installation

### Local Installation

```bash
# Clone the repository
git clone <repository-url>
cd skills/video-frames

# Install Python dependencies
pip install numpy pillow opencv-python

# Ensure FFmpeg is installed
ffmpeg -version
```

### Docker Installation

```bash
# CPU-only version
docker build -t video-frames --target production .

# GPU-accelerated version (NVIDIA)
docker build -t video-frames:gpu --target production-gpu .

# Using Docker Compose
docker-compose up video-frames-cpu
```

## Quick Start

### Python API

```python
from skills.video_frames import VideoProcessor, ExtractionConfig

# Create processor
processor = VideoProcessor()

# Extract metadata
metadata = processor.get_metadata("video.mp4")
print(f"Duration: {metadata.duration}s, Resolution: {metadata.width}x{metadata.height}")

# Extract frames
config = ExtractionConfig(fps=1)  # 1 frame per second
frames = processor.extract_frames("video.mp4", "output/frames/", config)

# Generate thumbnail
processor.generate_thumbnail("video.mp4", "output/thumb.jpg", time=5.0)

# Extract audio
processor.extract_audio("video.mp4", "output/audio.mp3")

# Detect scenes
scenes = processor.detect_scenes("video.mp4", threshold=0.3)

# Summarize video
summary = processor.summarize_video("video.mp4", "output/summary/", num_keyframes=5)
```

### Cell 0 OS Skill API

```python
from cell0os import get_skill

# Get the skill
video_skill = get_skill("video-frames")

# Extract frames
result = await video_skill.extract_frames({
    "video_path": "video.mp4",
    "output_dir": "output/frames/",
    "fps": 1,
    "format": "jpg"
})

# Get metadata
metadata = await video_skill.get_metadata({
    "video_path": "video.mp4"
})
```

## Configuration

### Skill Configuration (skill.yaml)

```yaml
category: media
dependencies:
  system:
    - ffmpeg (>=4.4)
    - ffprobe (>=4.4)

configuration:
  default_output_format: "jpg"
  default_frame_rate: 1
  default_quality: 95
  gpu_enabled: true
  gpu_device: "auto"  # auto, cuda, qsv, vaapi
  docker:
    enabled: false
    image: "jrottenberg/ffmpeg:latest"
    gpu_image: "jrottenberg/ffmpeg:nvidia"
```

### Environment Variables

```bash
# GPU acceleration
VIDEO_FRAMES_GPU_ENABLED=true
VIDEO_FRAMES_GPU_TYPE=cuda

# Paths
VIDEO_FRAMES_FFMPEG_PATH=/usr/bin/ffmpeg
VIDEO_FRAMES_FFPROBE_PATH=/usr/bin/ffprobe
VIDEO_FRAMES_TEMP_DIR=/tmp/video-frames

# Docker
VIDEO_FRAMES_DOCKER_ENABLED=true
VIDEO_FRAMES_DOCKER_IMAGE=jrottenberg/ffmpeg:latest

# Batch processing
VIDEO_FRAMES_MAX_CONCURRENT=4
```

## GPU Acceleration

### NVIDIA CUDA

```python
from skills.video_frames import VideoProcessor, GPUAccelType

processor = VideoProcessor(gpu_enabled=True)

# Check GPU type
print(processor._get_gpu_type())  # GPUAccelType.CUDA

# Convert with GPU acceleration
processor.convert_format(
    "input.mp4",
    "output.mp4",
    video_codec="h264",
    use_gpu=True
)
```

### Intel QSV / AMD VAAPI

```python
# Intel Quick Sync
processor = VideoProcessor(gpu_enabled=True)
# Automatically detects QSV/VAAPI if available
```

### Docker with GPU

```bash
# Run with NVIDIA GPU
docker run --gpus all -v $(pwd):/workspace video-frames:gpu

# Using docker-compose
docker-compose up video-frames-gpu
```

## API Reference

### VideoProcessor

Main class for video processing operations.

#### Methods

| Method | Description |
|--------|-------------|
| `get_metadata(video_path)` | Extract video metadata |
| `extract_frames(video_path, output_dir, config)` | Extract frames from video |
| `extract_audio(video_path, output_path, **kwargs)` | Extract audio track |
| `detect_scenes(video_path, **kwargs)` | Detect scene changes |
| `generate_thumbnail(video_path, output_path, **kwargs)` | Generate thumbnail |
| `convert_format(input_path, output_path, **kwargs)` | Convert video format |
| `extract_clip(video_path, output_path, start_time, end_time)` | Extract video clip |
| `summarize_video(video_path, output_dir, **kwargs)` | Generate video summary |
| `batch_process(video_paths, operation, output_dir, **kwargs)` | Batch process videos |

### ExtractionConfig

Configuration for frame extraction.

```python
config = ExtractionConfig(
    output_format=ImageFormat.JPG,  # JPG, PNG, WEBP
    quality=95,
    width=1920,
    height=1080,
    fps=1.0,
    start_time=0.0,
    end_time=60.0,
    use_gpu=False,
    scene_based=False,
    scene_threshold=0.3
)
```

## Examples

### Extract Every Nth Frame

```python
config = ExtractionConfig(fps=0.5)  # Every 2 seconds
frames = processor.extract_frames("video.mp4", "frames/", config)
```

### Scene-Based Frame Extraction

```python
config = ExtractionConfig(
    scene_based=True,
    scene_threshold=0.3
)
frames = processor.extract_frames("video.mp4", "scenes/", config)
```

### Batch Convert Videos

```python
import glob

videos = glob.glob("input/*.mp4")
results = processor.batch_process(
    videos,
    "convert",
    "output/",
    video_codec="h264",
    audio_codec="aac",
    use_gpu=True
)
```

### Custom Thumbnail Size

```python
processor.generate_thumbnail(
    "video.mp4",
    "thumb.jpg",
    time=10.5,
    width=320,
    height=180,
    quality=90
)
```

## Testing

```bash
# Run all tests
pytest tests/test_skill_video_frames.py -v

# Run with coverage
pytest tests/test_skill_video_frames.py --cov=skills.video_frames

# Run integration tests
pytest tests/test_skill_video_frames.py -m integration -v

# Run in Docker
docker-compose up video-frames-test
```

## Docker Compose Services

| Service | Description |
|---------|-------------|
| `video-frames-cpu` | CPU-only processing |
| `video-frames-gpu` | GPU-accelerated processing |
| `video-frames-dev` | Development environment |
| `video-frames-test` | Test runner |
| `video-frames-worker` | Batch processing worker |

## Troubleshooting

### FFmpeg Not Found

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### GPU Not Detected

```bash
# NVIDIA - check CUDA
docker run --gpus all nvidia/cuda:11.8.0-base nvidia-smi

# Check FFmpeg GPU encoders
ffmpeg -encoders | grep -E "(nvenc|qsv|vaapi)"
```

### Permission Denied in Docker

```bash
# Run with user permissions
docker run -u $(id -u):$(id -g) -v $(pwd):/workspace video-frames
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.
