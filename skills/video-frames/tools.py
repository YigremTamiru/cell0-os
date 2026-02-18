"""
Video Frames Skill - Tools for Agents
Cell 0 OS - Video Analysis via FFmpeg

This module provides low-level video processing utilities that can be used
by agents for video analysis tasks.
"""

import os
import re
import json
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Iterator
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

# Optional imports for advanced features
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


logger = logging.getLogger(__name__)


class GPUAccelType(Enum):
    """GPU acceleration types supported."""
    NONE = "none"
    CUDA = "cuda"
    QSV = "qsv"  # Intel Quick Sync
    VAAPI = "vaapi"  # AMD/Intel VAAPI
    OPENCL = "opencl"
    AUTO = "auto"


class VideoFormat(Enum):
    """Supported video formats."""
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MOV = "mov"
    WEBM = "webm"
    FLV = "flv"
    WMV = "wmv"
    MPEG = "mpeg"
    GIF = "gif"


class AudioFormat(Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    AAC = "aac"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    M4A = "m4a"
    OPUS = "opus"


class ImageFormat(Enum):
    """Supported image formats for frames."""
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"


@dataclass
class VideoMetadata:
    """Video metadata structure."""
    filename: str
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    bitrate: int = 0
    codec: str = ""
    audio_codec: str = ""
    audio_channels: int = 0
    audio_sample_rate: int = 0
    format_name: str = ""
    file_size: int = 0
    has_video: bool = True
    has_audio: bool = False
    rotation: int = 0
    extra: Dict = field(default_factory=dict)


@dataclass
class FrameInfo:
    """Information about an extracted frame."""
    frame_number: int
    timestamp: float
    file_path: str
    width: int = 0
    height: int = 0
    is_keyframe: bool = False


@dataclass
class SceneInfo:
    """Scene detection result."""
    start_time: float
    end_time: float
    start_frame: int
    end_frame: int
    thumbnail_path: Optional[str] = None
    score: float = 0.0


@dataclass
class ExtractionConfig:
    """Configuration for frame extraction."""
    output_format: ImageFormat = ImageFormat.JPG
    quality: int = 95
    width: Optional[int] = None
    height: Optional[int] = None
    maintain_aspect: bool = True
    fps: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    use_gpu: bool = False
    gpu_type: GPUAccelType = GPUAccelType.AUTO
    scene_based: bool = False
    scene_threshold: float = 0.3


class VideoProcessor:
    """Main video processing class with FFmpeg integration."""
    
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        temp_dir: Optional[str] = None,
        use_docker: bool = False,
        docker_image: str = "jrottenberg/ffmpeg:latest",
        gpu_enabled: bool = False
    ):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.use_docker = use_docker
        self.docker_image = docker_image
        self.gpu_enabled = gpu_enabled
        self._docker_checked = False
        self._gpu_available = None
        
    def _get_ffmpeg_cmd(self) -> List[str]:
        """Get FFmpeg command, with Docker support if enabled."""
        if self.use_docker:
            if not self._docker_checked:
                self._check_docker()
            
            gpu_args = []
            if self.gpu_enabled and self._get_gpu_type() == GPUAccelType.CUDA:
                gpu_args = ["--gpus", "all"]
            
            return [
                "docker", "run", "--rm",
                *gpu_args,
                "-v", f"{os.getcwd()}:/workspace",
                "-w", "/workspace",
                self.docker_image,
                "ffmpeg"
            ]
        return [self.ffmpeg_path]
    
    def _get_ffprobe_cmd(self) -> List[str]:
        """Get FFprobe command, with Docker support if enabled."""
        if self.use_docker:
            return [
                "docker", "run", "--rm",
                "-v", f"{os.getcwd()}:/workspace",
                "-w", "/workspace",
                self.docker_image,
                "ffprobe"
            ]
        return [self.ffprobe_path]
    
    def _check_docker(self):
        """Check if Docker is available."""
        try:
            subprocess.run(
                ["docker", "--version"],
                check=True,
                capture_output=True,
                timeout=10
            )
            self._docker_checked = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("Docker not available but use_docker=True")
    
    def _get_gpu_type(self) -> GPUAccelType:
        """Detect available GPU acceleration."""
        if self._gpu_available is not None:
            return self._gpu_available
            
        if not self.gpu_enabled:
            self._gpu_available = GPUAccelType.NONE
            return GPUAccelType.NONE
        
        # Check for NVIDIA CUDA
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self._gpu_available = GPUAccelType.CUDA
                return GPUAccelType.CUDA
        except FileNotFoundError:
            pass
        
        # Check for Intel QSV
        try:
            result = subprocess.run(
                self._get_ffmpeg_cmd() + ["-hwaccels"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "qsv" in result.stdout:
                self._gpu_available = GPUAccelType.QSV
                return GPUAccelType.QSV
            if "vaapi" in result.stdout:
                self._gpu_available = GPUAccelType.VAAPI
                return GPUAccelType.VAAPI
        except Exception:
            pass
        
        self._gpu_available = GPUAccelType.NONE
        return GPUAccelType.NONE
    
    def _get_gpu_encoder(self, codec: str = "h264") -> str:
        """Get GPU-accelerated encoder for codec."""
        gpu = self._get_gpu_type()
        
        encoders = {
            (GPUAccelType.CUDA, "h264"): "h264_nvenc",
            (GPUAccelType.CUDA, "hevc"): "hevc_nvenc",
            (GPUAccelType.QSV, "h264"): "h264_qsv",
            (GPUAccelType.QSV, "hevc"): "hevc_qsv",
            (GPUAccelType.VAAPI, "h264"): "h264_vaapi",
            (GPUAccelType.VAAPI, "hevc"): "hevc_vaapi",
        }
        
        return encoders.get((gpu, codec), f"libx{codec}")
    
    def get_metadata(self, video_path: str) -> VideoMetadata:
        """Extract comprehensive video metadata."""
        cmd = self._get_ffprobe_cmd() + [
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-print_format", "json",
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr}")
        
        data = json.loads(result.stdout)
        
        metadata = VideoMetadata(
            filename=os.path.basename(video_path),
            file_size=int(data.get('format', {}).get('size', 0))
        )
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                metadata.has_video = True
                metadata.width = stream.get('width', 0)
                metadata.height = stream.get('height', 0)
                metadata.codec = stream.get('codec_name', '')
                metadata.bitrate = int(stream.get('bit_rate', 0))
                
                # Parse FPS
                fps_str = stream.get('r_frame_rate', '0/1')
                try:
                    num, den = map(int, fps_str.split('/'))
                    metadata.fps = num / den if den else 0
                except (ValueError, ZeroDivisionError):
                    metadata.fps = 0
                
                # Duration
                if 'duration' in stream:
                    metadata.duration = float(stream['duration'])
                elif 'duration' in data.get('format', {}):
                    metadata.duration = float(data['format']['duration'])
                
                # Rotation
                side_data = stream.get('side_data_list', [])
                for sd in side_data:
                    if sd.get('rotation'):
                        metadata.rotation = int(sd['rotation'])
                        
            elif stream.get('codec_type') == 'audio':
                metadata.has_audio = True
                metadata.audio_codec = stream.get('codec_name', '')
                metadata.audio_channels = stream.get('channels', 0)
                metadata.audio_sample_rate = stream.get('sample_rate', 0)
        
        metadata.format_name = data.get('format', {}).get('format_name', '')
        metadata.extra = data
        
        return metadata
    
    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        config: Optional[ExtractionConfig] = None
    ) -> List[FrameInfo]:
        """Extract frames from video with various options."""
        config = config or ExtractionConfig()
        os.makedirs(output_dir, exist_ok=True)
        
        metadata = self.get_metadata(video_path)
        
        # Build FFmpeg command
        cmd = self._get_ffmpeg_cmd()
        
        # Input options
        input_opts = ["-i", video_path]
        
        # Time range
        if config.start_time is not None:
            input_opts = ["-ss", str(config.start_time)] + input_opts
        if config.end_time is not None:
            input_opts.extend(["-to", str(config.end_time)])
        
        cmd.extend(input_opts)
        
        # Video filters
        filters = []
        
        # GPU decoding
        if config.use_gpu and self._get_gpu_type() == GPUAccelType.CUDA:
            filters.append("hwupload_cuda")
        
        # Scaling
        if config.width or config.height:
            width = config.width or -1
            height = config.height or -1
            if config.maintain_aspect:
                filters.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
            else:
                filters.append(f"scale={width}:{height}")
        
        # Frame rate selection
        if config.fps:
            filters.append(f"fps={config.fps}")
        
        # Output format options
        output_opts = []
        if filters:
            output_opts.extend(["-vf", ",".join(filters)])
        
        # Quality settings
        ext = config.output_format.value
        if ext in ['jpg', 'jpeg']:
            output_opts.extend(["-q:v", str(max(1, min(31, int((100 - config.quality) / 3.23))))])
        elif ext == 'png':
            output_opts.extend(["-compression_level", str(max(0, min(9, int((100 - config.quality) / 11))))])
        elif ext == 'webp':
            output_opts.extend(["-q:v", str(config.quality)])
        
        # Output pattern
        output_pattern = os.path.join(output_dir, f"frame_%06d.{ext}")
        cmd.extend(output_opts + [output_pattern])
        
        # Execute
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Frame extraction failed: {result.stderr}")
        
        # Collect frame info
        frames = []
        frame_files = sorted(Path(output_dir).glob(f"frame_*.{ext}"))
        
        for i, frame_file in enumerate(frame_files):
            timestamp = i / (config.fps or metadata.fps) if metadata.fps else 0
            if config.start_time:
                timestamp += config.start_time
                
            frame_info = FrameInfo(
                frame_number=i,
                timestamp=timestamp,
                file_path=str(frame_file)
            )
            
            # Get dimensions if PIL available
            if HAS_PIL:
                try:
                    with Image.open(frame_file) as img:
                        frame_info.width, frame_info.height = img.size
                except Exception:
                    pass
            
            frames.append(frame_info)
        
        return frames
    
    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        format: AudioFormat = AudioFormat.MP3,
        bitrate: str = "192k",
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None
    ) -> Dict:
        """Extract audio from video."""
        cmd = self._get_ffmpeg_cmd()
        
        # Input
        cmd.extend(["-i", video_path])
        
        # Audio codec selection
        codec_map = {
            AudioFormat.MP3: "libmp3lame",
            AudioFormat.AAC: "aac",
            AudioFormat.WAV: "pcm_s16le",
            AudioFormat.FLAC: "flac",
            AudioFormat.OGG: "libvorbis",
            AudioFormat.M4A: "aac",
            AudioFormat.OPUS: "libopus"
        }
        
        cmd.extend(["-vn", "-c:a", codec_map.get(format, "copy")])
        
        # Bitrate
        cmd.extend(["-b:a", bitrate])
        
        # Sample rate
        if sample_rate:
            cmd.extend(["-ar", str(sample_rate)])
        
        # Channels
        if channels:
            cmd.extend(["-ac", str(channels)])
        
        # Output
        cmd.append(output_path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Audio extraction failed: {result.stderr}")
        
        return {
            "output_path": output_path,
            "format": format.value,
            "bitrate": bitrate
        }
    
    def detect_scenes(
        self,
        video_path: str,
        threshold: float = 0.3,
        min_scene_duration: float = 0.5
    ) -> List[SceneInfo]:
        """Detect scene changes in video using FFmpeg scenedetect filter."""
        cmd = self._get_ffprobe_cmd() + [
            "-show_frames",
            "-show_entries", "frame=pkt_pts_time,pict_type",
            "-of", "json",
            "-f", "lavfi",
            f"movie={video_path},select=gt(scene\\,{threshold})",
            "-v", "quiet"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        scenes = []
        metadata = self.get_metadata(video_path)
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                frames = data.get('frames', [])
                
                prev_time = 0.0
                for i, frame in enumerate(frames):
                    time = float(frame.get('pkt_pts_time', 0))
                    
                    if time - prev_time >= min_scene_duration:
                        scene = SceneInfo(
                            start_time=prev_time,
                            end_time=time,
                            start_frame=int(prev_time * metadata.fps),
                            end_frame=int(time * metadata.fps),
                            score=threshold
                        )
                        scenes.append(scene)
                    
                    prev_time = time
                
                # Add final scene
                if prev_time < metadata.duration:
                    scenes.append(SceneInfo(
                        start_time=prev_time,
                        end_time=metadata.duration,
                        start_frame=int(prev_time * metadata.fps),
                        end_frame=int(metadata.duration * metadata.fps)
                    ))
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Scene detection parsing failed: {e}")
        
        # Fallback: Use keyframe-based scene detection
        if not scenes:
            scenes = self._detect_scenes_keyframes(video_path, min_scene_duration)
        
        return scenes
    
    def _detect_scenes_keyframes(
        self,
        video_path: str,
        min_duration: float
    ) -> List[SceneInfo]:
        """Fallback scene detection using keyframes."""
        metadata = self.get_metadata(video_path)
        
        # Generate scenes every N seconds as fallback
        scene_duration = max(min_duration, metadata.duration / 10)
        scenes = []
        
        current_time = 0.0
        while current_time < metadata.duration:
            end_time = min(current_time + scene_duration, metadata.duration)
            scenes.append(SceneInfo(
                start_time=current_time,
                end_time=end_time,
                start_frame=int(current_time * metadata.fps),
                end_frame=int(end_time * metadata.fps)
            ))
            current_time = end_time
        
        return scenes
    
    def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        time: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: int = 95
    ) -> Dict:
        """Generate video thumbnail at specified time."""
        metadata = self.get_metadata(video_path)
        
        # Default to middle of video
        if time is None:
            time = metadata.duration / 2
        
        cmd = self._get_ffmpeg_cmd()
        
        # Seek to time
        cmd.extend(["-ss", str(time)])
        
        # Input (seek before input for faster processing)
        cmd.extend(["-i", video_path, "-frames:v", "1"])
        
        # Filters
        filters = []
        if width or height:
            w = width or -1
            h = height or -1
            filters.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease")
        
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # Quality
        ext = Path(output_path).suffix.lower().lstrip('.')
        if ext in ['jpg', 'jpeg']:
            cmd.extend(["-q:v", str(max(1, min(31, int((100 - quality) / 3.23))))])
        
        cmd.append(output_path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Thumbnail generation failed: {result.stderr}")
        
        return {
            "output_path": output_path,
            "timestamp": time,
            "width": width,
            "height": height
        }
    
    def convert_format(
        self,
        input_path: str,
        output_path: str,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        video_bitrate: Optional[str] = None,
        audio_bitrate: Optional[str] = None,
        use_gpu: bool = False,
        preset: str = "medium",
        crf: Optional[int] = None
    ) -> Dict:
        """Convert video format with optional GPU acceleration."""
        cmd = self._get_ffmpeg_cmd()
        cmd.extend(["-i", input_path])
        
        # Video codec
        if video_codec:
            if use_gpu and video_codec in ['h264', 'hevc', 'h265']:
                encoder = self._get_gpu_encoder(video_codec.replace('h265', 'hevc'))
                cmd.extend(["-c:v", encoder])
                
                # GPU-specific settings
                if self._get_gpu_type() == GPUAccelType.CUDA:
                    cmd.extend(["-preset", preset, "-rc:v", "vbr_hq"])
            else:
                cmd.extend(["-c:v", f"libx{video_codec.replace('h265', '265')}"])
                cmd.extend(["-preset", preset])
                if crf:
                    cmd.extend(["-crf", str(crf)])
        else:
            cmd.append("-c:v")  # Copy video
        
        # Audio codec
        if audio_codec:
            cmd.extend(["-c:a", audio_codec])
            if audio_bitrate:
                cmd.extend(["-b:a", audio_bitrate])
        else:
            cmd.append("-c:a")  # Copy audio
        
        # Video bitrate
        if video_bitrate:
            cmd.extend(["-b:v", video_bitrate])
        
        cmd.append(output_path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Format conversion failed: {result.stderr}")
        
        return {
            "input_path": input_path,
            "output_path": output_path,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "used_gpu": use_gpu and self._get_gpu_type() != GPUAccelType.NONE
        }
    
    def extract_clip(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        reencode: bool = True
    ) -> Dict:
        """Extract a clip from video."""
        cmd = self._get_ffmpeg_cmd()
        
        # Time range
        cmd.extend(["-ss", str(start_time)])
        cmd.extend(["-i", video_path])
        cmd.extend(["-to", str(end_time - start_time)])
        
        # Copy or re-encode
        if reencode:
            cmd.extend(["-c:v", "libx264", "-c:a", "aac"])
        else:
            cmd.extend(["-c", "copy"])
        
        cmd.append(output_path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Clip extraction failed: {result.stderr}")
        
        return {
            "output_path": output_path,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time
        }
    
    def summarize_video(
        self,
        video_path: str,
        output_dir: str,
        num_keyframes: int = 5,
        include_scenes: bool = True
    ) -> Dict:
        """Generate video summary with key frames."""
        os.makedirs(output_dir, exist_ok=True)
        
        metadata = self.get_metadata(video_path)
        
        # Get scenes or create uniform segments
        if include_scenes:
            scenes = self.detect_scenes(video_path)
        else:
            segment_duration = metadata.duration / num_keyframes
            scenes = [
                SceneInfo(
                    start_time=i * segment_duration,
                    end_time=(i + 1) * segment_duration,
                    start_frame=int(i * segment_duration * metadata.fps),
                    end_frame=int((i + 1) * segment_duration * metadata.fps)
                )
                for i in range(num_keyframes)
            ]
        
        # Select representative frames
        keyframes = []
        for i, scene in enumerate(scenes[:num_keyframes]):
            # Use middle of scene
            mid_time = (scene.start_time + scene.end_time) / 2
            
            output_path = os.path.join(output_dir, f"keyframe_{i:03d}.jpg")
            self.generate_thumbnail(
                video_path,
                output_path,
                time=mid_time,
                quality=95
            )
            
            keyframes.append({
                "frame_number": i,
                "timestamp": mid_time,
                "file_path": output_path,
                "scene_start": scene.start_time,
                "scene_end": scene.end_time
            })
        
        return {
            "video_path": video_path,
            "output_dir": output_dir,
            "duration": metadata.duration,
            "num_keyframes": len(keyframes),
            "keyframes": keyframes,
            "scenes_detected": len(scenes)
        }
    
    def batch_process(
        self,
        video_paths: List[str],
        operation: str,
        output_dir: str,
        **kwargs
    ) -> List[Dict]:
        """Process multiple videos in batch."""
        os.makedirs(output_dir, exist_ok=True)
        results = []
        
        for video_path in video_paths:
            try:
                video_name = Path(video_path).stem
                result = {"input": video_path, "success": False}
                
                if operation == "extract_frames":
                    out_dir = os.path.join(output_dir, video_name)
                    config = kwargs.get('config', ExtractionConfig())
                    frames = self.extract_frames(video_path, out_dir, config)
                    result.update({
                        "success": True,
                        "output_dir": out_dir,
                        "frames_extracted": len(frames)
                    })
                
                elif operation == "extract_audio":
                    fmt = kwargs.get('format', AudioFormat.MP3)
                    out_path = os.path.join(output_dir, f"{video_name}.{fmt.value}")
                    info = self.extract_audio(video_path, out_path, fmt)
                    result.update({"success": True, **info})
                
                elif operation == "thumbnail":
                    out_path = os.path.join(output_dir, f"{video_name}.jpg")
                    info = self.generate_thumbnail(video_path, out_path)
                    result.update({"success": True, **info})
                
                elif operation == "convert":
                    fmt = kwargs.get('format', 'mp4')
                    out_path = os.path.join(output_dir, f"{video_name}.{fmt}")
                    info = self.convert_format(video_path, out_path, **kwargs)
                    result.update({"success": True, **info})
                
                elif operation == "metadata":
                    meta = self.get_metadata(video_path)
                    result.update({
                        "success": True,
                        "metadata": asdict(meta)
                    })
                
                else:
                    result["error"] = f"Unknown operation: {operation}"
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    "input": video_path,
                    "success": False,
                    "error": str(e)
                })
        
        return results


# Convenience functions for direct use
def create_processor(**kwargs) -> VideoProcessor:
    """Create a VideoProcessor instance."""
    return VideoProcessor(**kwargs)


def quick_metadata(video_path: str) -> VideoMetadata:
    """Quickly get video metadata."""
    return create_processor().get_metadata(video_path)


def quick_thumbnail(video_path: str, output_path: str, **kwargs) -> Dict:
    """Quickly generate a thumbnail."""
    return create_processor().generate_thumbnail(video_path, output_path, **kwargs)


def quick_frames(video_path: str, output_dir: str, **kwargs) -> List[FrameInfo]:
    """Quickly extract frames from video."""
    config = ExtractionConfig(**kwargs)
    return create_processor().extract_frames(video_path, output_dir, config)
