"""
Video Frames Skill - Cell 0 OS
Advanced video processing using FFmpeg with GPU acceleration support.

This package provides comprehensive video analysis capabilities including:
- Frame extraction
- Audio extraction
- Scene detection
- Video summarization
- Thumbnail generation
- Format conversion
- Clip extraction
- Metadata extraction
- Batch processing

Usage:
    from skills.video_frames import VideoProcessor, ExtractionConfig
    
    processor = VideoProcessor()
    
    # Extract metadata
    metadata = processor.get_metadata("video.mp4")
    
    # Extract frames
    config = ExtractionConfig(fps=1)
    frames = processor.extract_frames("video.mp4", "output/", config)
    
    # Generate thumbnail
    processor.generate_thumbnail("video.mp4", "thumb.jpg")
"""

from .tools import (
    VideoProcessor,
    ExtractionConfig,
    GPUAccelType,
    VideoFormat,
    AudioFormat,
    ImageFormat,
    VideoMetadata,
    FrameInfo,
    SceneInfo,
    create_processor,
    quick_metadata,
    quick_thumbnail,
    quick_frames
)

try:
    from .video_frames_skill import (
        VideoFramesSkill,
        create_skill,
        SKILL_MANIFEST
    )
except ImportError:
    # Cell 0 OS dependencies may not be available
    pass

__version__ = "1.0.0"
__author__ = "Cell 0 OS"

__all__ = [
    # Core classes
    "VideoProcessor",
    "ExtractionConfig",
    "VideoMetadata",
    "FrameInfo",
    "SceneInfo",
    
    # Enums
    "GPUAccelType",
    "VideoFormat",
    "AudioFormat",
    "ImageFormat",
    
    # Convenience functions
    "create_processor",
    "quick_metadata",
    "quick_thumbnail",
    "quick_frames",
    
    # Skill classes (if Cell 0 OS available)
    "VideoFramesSkill",
    "create_skill",
    "SKILL_MANIFEST",
]
