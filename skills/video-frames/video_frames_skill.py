"""
Video Frames Skill - Main Skill Module
Cell 0 OS - Video Analysis via FFmpeg

This skill provides comprehensive video processing capabilities including:
- Frame extraction
- Audio extraction
- Scene detection
- Video summarization
- Thumbnail generation
- Format conversion
- Clip extraction
- Metadata extraction
- Batch processing

With GPU acceleration support via CUDA, QSV, and VAAPI.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

# Cell 0 OS imports
from cell0os.skills.base import BaseSkill, SkillRequest, SkillResponse
from cell0os.skills.decorators import endpoint, timer, require_capability

# Local tools
from .tools import (
    VideoProcessor,
    ExtractionConfig,
    GPUAccelType,
    VideoFormat,
    AudioFormat,
    ImageFormat,
    VideoMetadata,
    FrameInfo,
    SceneInfo
)


@dataclass
class VideoFrameExtractionRequest:
    """Request for frame extraction."""
    video_path: str
    output_dir: str
    format: str = "jpg"
    quality: int = 95
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    use_gpu: bool = False
    scene_based: bool = False
    scene_threshold: float = 0.3


@dataclass
class AudioExtractionRequest:
    """Request for audio extraction."""
    video_path: str
    output_path: str
    format: str = "mp3"
    bitrate: str = "192k"
    sample_rate: Optional[int] = None
    channels: Optional[int] = None


@dataclass
class SceneDetectionRequest:
    """Request for scene detection."""
    video_path: str
    threshold: float = 0.3
    min_scene_duration: float = 0.5


@dataclass
class ThumbnailRequest:
    """Request for thumbnail generation."""
    video_path: str
    output_path: str
    time: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    quality: int = 95


@dataclass
class FormatConversionRequest:
    """Request for format conversion."""
    input_path: str
    output_path: str
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    video_bitrate: Optional[str] = None
    audio_bitrate: Optional[str] = None
    use_gpu: bool = False
    preset: str = "medium"
    crf: Optional[int] = None


@dataclass
class ClipExtractionRequest:
    """Request for clip extraction."""
    video_path: str
    output_path: str
    start_time: float
    end_time: float
    reencode: bool = True


@dataclass
class MetadataRequest:
    """Request for metadata extraction."""
    video_path: str
    include_extra: bool = False


@dataclass
class VideoSummarizationRequest:
    """Request for video summarization."""
    video_path: str
    output_dir: str
    num_keyframes: int = 5
    include_scenes: bool = True


@dataclass
class BatchProcessingRequest:
    """Request for batch processing."""
    video_paths: List[str]
    operation: str  # extract_frames, extract_audio, thumbnail, convert, metadata
    output_dir: str
    operation_config: Dict[str, Any] = None


class VideoFramesSkill(BaseSkill):
    """
    Video Frames Skill for Cell 0 OS.
    
    Provides comprehensive video processing capabilities using FFmpeg
    with optional Docker support and GPU acceleration.
    """
    
    SKILL_NAME = "video-frames"
    SKILL_VERSION = "1.0.0"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        
        self.config = config or {}
        self._processor = None
        self._init_processor()
        
    def _init_processor(self):
        """Initialize the video processor."""
        self._processor = VideoProcessor(
            ffmpeg_path=self.config.get('ffmpeg_path', 'ffmpeg'),
            ffprobe_path=self.config.get('ffprobe_path', 'ffprobe'),
            temp_dir=self.config.get('temp_directory', '/tmp/video-frames'),
            use_docker=self.config.get('docker', {}).get('enabled', False),
            docker_image=self.config.get('docker', {}).get(
                'image', 'jrottenberg/ffmpeg:latest'
            ),
            gpu_enabled=self.config.get('gpu_enabled', True)
        )
    
    @property
    def processor(self) -> VideoProcessor:
        """Get or create video processor."""
        if self._processor is None:
            self._init_processor()
        return self._processor
    
    @endpoint("extract_frames")
    async def extract_frames(
        self,
        request: VideoFrameExtractionRequest
    ) -> SkillResponse:
        """
        Extract frames from a video file.
        
        Supports various options including FPS control, time ranges,
        scaling, and scene-based extraction.
        """
        try:
            # Validate input
            if not os.path.exists(request.video_path):
                return SkillResponse.error(
                    f"Video file not found: {request.video_path}"
                )
            
            # Create extraction config
            config = ExtractionConfig(
                output_format=ImageFormat(request.format.lower()),
                quality=request.quality,
                width=request.width,
                height=request.height,
                fps=request.fps,
                start_time=request.start_time,
                end_time=request.end_time,
                use_gpu=request.use_gpu,
                scene_based=request.scene_based,
                scene_threshold=request.scene_threshold
            )
            
            # Extract frames
            frames = self.processor.extract_frames(
                request.video_path,
                request.output_dir,
                config
            )
            
            # Build response
            frame_data = [
                {
                    "frame_number": f.frame_number,
                    "timestamp": f.timestamp,
                    "file_path": f.file_path,
                    "width": f.width,
                    "height": f.height
                }
                for f in frames
            ]
            
            return SkillResponse.success({
                "video_path": request.video_path,
                "output_dir": request.output_dir,
                "frames_extracted": len(frames),
                "frames": frame_data
            })
            
        except Exception as e:
            return SkillResponse.error(
                f"Frame extraction failed: {str(e)}"
            )
    
    @endpoint("extract_audio")
    async def extract_audio(
        self,
        request: AudioExtractionRequest
    ) -> SkillResponse:
        """
        Extract audio from a video file.
        
        Supports multiple output formats and quality settings.
        """
        try:
            if not os.path.exists(request.video_path):
                return SkillResponse.error(
                    f"Video file not found: {request.video_path}"
                )
            
            result = self.processor.extract_audio(
                request.video_path,
                request.output_path,
                format=AudioFormat(request.format.lower()),
                bitrate=request.bitrate,
                sample_rate=request.sample_rate,
                channels=request.channels
            )
            
            return SkillResponse.success(result)
            
        except Exception as e:
            return SkillResponse.error(
                f"Audio extraction failed: {str(e)}"
            )
    
    @endpoint("detect_scenes")
    async def detect_scenes(
        self,
        request: SceneDetectionRequest
    ) -> SkillResponse:
        """
        Detect scene changes in a video.
        
        Uses FFmpeg's scene detection filter to identify
        scene transitions with configurable threshold.
        """
        try:
            if not os.path.exists(request.video_path):
                return SkillResponse.error(
                    f"Video file not found: {request.video_path}"
                )
            
            scenes = self.processor.detect_scenes(
                request.video_path,
                threshold=request.threshold,
                min_scene_duration=request.min_scene_duration
            )
            
            scene_data = [
                {
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "start_frame": s.start_frame,
                    "end_frame": s.end_frame,
                    "duration": s.end_time - s.start_time,
                    "score": s.score
                }
                for s in scenes
            ]
            
            return SkillResponse.success({
                "video_path": request.video_path,
                "scenes_detected": len(scenes),
                "scenes": scene_data
            })
            
        except Exception as e:
            return SkillResponse.error(
                f"Scene detection failed: {str(e)}"
            )
    
    @endpoint("generate_thumbnail")
    async def generate_thumbnail(
        self,
        request: ThumbnailRequest
    ) -> SkillResponse:
        """
        Generate a thumbnail from a video.
        
        Can extract at specific time or default to middle of video.
        Supports resizing and quality control.
        """
        try:
            if not os.path.exists(request.video_path):
                return SkillResponse.error(
                    f"Video file not found: {request.video_path}"
                )
            
            result = self.processor.generate_thumbnail(
                request.video_path,
                request.output_path,
                time=request.time,
                width=request.width,
                height=request.height,
                quality=request.quality
            )
            
            return SkillResponse.success(result)
            
        except Exception as e:
            return SkillResponse.error(
                f"Thumbnail generation failed: {str(e)}"
            )
    
    @endpoint("convert_format")
    async def convert_format(
        self,
        request: FormatConversionRequest
    ) -> SkillResponse:
        """
        Convert video format.
        
        Supports codec selection, bitrate control, and GPU acceleration
        for faster transcoding.
        """
        try:
            if not os.path.exists(request.input_path):
                return SkillResponse.error(
                    f"Input file not found: {request.input_path}"
                )
            
            result = self.processor.convert_format(
                request.input_path,
                request.output_path,
                video_codec=request.video_codec,
                audio_codec=request.audio_codec,
                video_bitrate=request.video_bitrate,
                audio_bitrate=request.audio_bitrate,
                use_gpu=request.use_gpu,
                preset=request.preset,
                crf=request.crf
            )
            
            return SkillResponse.success(result)
            
        except Exception as e:
            return SkillResponse.error(
                f"Format conversion failed: {str(e)}"
            )
    
    @endpoint("extract_clip")
    async def extract_clip(
        self,
        request: ClipExtractionRequest
    ) -> SkillResponse:
        """
        Extract a clip from a video.
        
        Extracts a time segment with optional re-encoding.
        """
        try:
            if not os.path.exists(request.video_path):
                return SkillResponse.error(
                    f"Video file not found: {request.video_path}"
                )
            
            result = self.processor.extract_clip(
                request.video_path,
                request.output_path,
                start_time=request.start_time,
                end_time=request.end_time,
                reencode=request.reencode
            )
            
            return SkillResponse.success(result)
            
        except Exception as e:
            return SkillResponse.error(
                f"Clip extraction failed: {str(e)}"
            )
    
    @endpoint("get_metadata")
    async def get_metadata(
        self,
        request: MetadataRequest
    ) -> SkillResponse:
        """
        Extract video metadata.
        
        Returns comprehensive metadata including duration, dimensions,
        codecs, bitrate, and more.
        """
        try:
            if not os.path.exists(request.video_path):
                return SkillResponse.error(
                    f"Video file not found: {request.video_path}"
                )
            
            metadata = self.processor.get_metadata(request.video_path)
            
            result = {
                "filename": metadata.filename,
                "duration": metadata.duration,
                "width": metadata.width,
                "height": metadata.height,
                "fps": metadata.fps,
                "bitrate": metadata.bitrate,
                "codec": metadata.codec,
                "audio_codec": metadata.audio_codec,
                "audio_channels": metadata.audio_channels,
                "audio_sample_rate": metadata.audio_sample_rate,
                "format_name": metadata.format_name,
                "file_size": metadata.file_size,
                "has_video": metadata.has_video,
                "has_audio": metadata.has_audio,
                "rotation": metadata.rotation
            }
            
            if request.include_extra:
                result["extra"] = metadata.extra
            
            return SkillResponse.success(result)
            
        except Exception as e:
            return SkillResponse.error(
                f"Metadata extraction failed: {str(e)}"
            )
    
    @endpoint("summarize_video")
    async def summarize_video(
        self,
        request: VideoSummarizationRequest
    ) -> SkillResponse:
        """
        Generate video summary with key frames.
        
        Extracts representative frames from detected scenes or
        uniform time intervals.
        """
        try:
            if not os.path.exists(request.video_path):
                return SkillResponse.error(
                    f"Video file not found: {request.video_path}"
                )
            
            result = self.processor.summarize_video(
                request.video_path,
                request.output_dir,
                num_keyframes=request.num_keyframes,
                include_scenes=request.include_scenes
            )
            
            return SkillResponse.success(result)
            
        except Exception as e:
            return SkillResponse.error(
                f"Video summarization failed: {str(e)}"
            )
    
    @endpoint("batch_process")
    async def batch_process(
        self,
        request: BatchProcessingRequest
    ) -> SkillResponse:
        """
        Process multiple videos in batch.
        
        Supports all operations: extract_frames, extract_audio,
        thumbnail, convert, metadata.
        """
        try:
            # Validate all inputs exist
            for path in request.video_paths:
                if not os.path.exists(path):
                    return SkillResponse.error(
                        f"Video file not found: {path}"
                    )
            
            config = request.operation_config or {}
            
            results = self.processor.batch_process(
                request.video_paths,
                request.operation,
                request.output_dir,
                **config
            )
            
            successful = sum(1 for r in results if r.get('success', False))
            failed = len(results) - successful
            
            return SkillResponse.success({
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "operation": request.operation,
                "results": results
            })
            
        except Exception as e:
            return SkillResponse.error(
                f"Batch processing failed: {str(e)}"
            )
    
    @timer(interval=60)
    async def health_check(self) -> Dict:
        """Periodic health check for the skill."""
        try:
            import subprocess
            result = subprocess.run(
                [self.config.get('ffmpeg_path', 'ffmpeg'), '-version'],
                capture_output=True,
                timeout=10
            )
            
            gpu_available = self.processor._get_gpu_type().value
            
            return {
                "status": "healthy" if result.returncode == 0 else "unhealthy",
                "ffmpeg_available": result.returncode == 0,
                "gpu_acceleration": gpu_available,
                "docker_enabled": self.config.get('docker', {}).get('enabled', False),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def initialize(self):
        """Initialize the skill."""
        await super().initialize()
        
        # Create temp directory
        temp_dir = self.config.get('temp_directory', '/tmp/video-frames')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Check FFmpeg availability
        try:
            health = await self.health_check()
            if health.get('ffmpeg_available'):
                self.logger.info("Video Frames Skill initialized successfully")
                self.logger.info(f"GPU acceleration: {health.get('gpu_acceleration')}")
            else:
                self.logger.warning("FFmpeg not available - some features may not work")
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
    
    async def shutdown(self):
        """Shutdown the skill."""
        self._processor = None
        await super().shutdown()


# Skill registration
def create_skill(config: Dict = None) -> VideoFramesSkill:
    """Factory function for creating the skill."""
    return VideoFramesSkill(config)


# Cell 0 OS skill manifest
SKILL_MANIFEST = {
    "name": "video-frames",
    "version": "1.0.0",
    "description": "Advanced video processing using FFmpeg with GPU acceleration",
    "entry_point": "video_frames_skill:create_skill",
    "endpoints": [
        "extract_frames",
        "extract_audio",
        "detect_scenes",
        "generate_thumbnail",
        "convert_format",
        "extract_clip",
        "get_metadata",
        "summarize_video",
        "batch_process"
    ],
    "capabilities": [
        "video_frame_extraction",
        "audio_extraction",
        "scene_detection",
        "video_summarization",
        "thumbnail_generation",
        "format_conversion",
        "clip_extraction",
        "metadata_extraction",
        "batch_processing",
        "gpu_acceleration"
    ],
    "config_schema": {
        "ffmpeg_path": {"type": "string", "default": "ffmpeg"},
        "ffprobe_path": {"type": "string", "default": "ffprobe"},
        "temp_directory": {"type": "string", "default": "/tmp/video-frames"},
        "gpu_enabled": {"type": "boolean", "default": True},
        "docker": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "default": False},
                "image": {"type": "string", "default": "jrottenberg/ffmpeg:latest"},
                "gpu_image": {"type": "string", "default": "jrottenberg/ffmpeg:nvidia"}
            }
        }
    }
}
