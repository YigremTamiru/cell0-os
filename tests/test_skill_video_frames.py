"""
Video Frames Skill - Test Suite
Cell 0 OS - Video Analysis via FFmpeg

Comprehensive tests for all video processing capabilities.
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add paths for imports - use relative paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'skills', 'video-frames'))
sys.path.insert(0, PROJECT_ROOT)

from tools import (
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
    quick_thumbnail
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def processor(temp_dir):
    """Create a VideoProcessor instance for testing."""
    return VideoProcessor(
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        temp_dir=temp_dir,
        use_docker=False,
        gpu_enabled=False
    )


@pytest.fixture
def sample_video(temp_dir):
    """Create a sample video for testing using FFmpeg."""
    video_path = os.path.join(temp_dir, "test_video.mp4")
    
    # Generate test video with FFmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=10:size=640x480:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=1000:duration=10",
        "-pix_fmt", "yuv420p",
        video_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            return video_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Skip tests if FFmpeg not available
    pytest.skip("FFmpeg not available for test video generation")


# ============================================================================
# Test VideoProcessor Initialization
# ============================================================================

class TestVideoProcessorInit:
    """Test VideoProcessor initialization."""
    
    def test_default_init(self, temp_dir):
        """Test default initialization."""
        proc = VideoProcessor(temp_dir=temp_dir)
        assert proc.ffmpeg_path == "ffmpeg"
        assert proc.ffprobe_path == "ffprobe"
        assert proc.temp_dir == temp_dir
        assert not proc.use_docker
        assert proc.gpu_enabled
    
    def test_custom_init(self, temp_dir):
        """Test custom initialization."""
        proc = VideoProcessor(
            ffmpeg_path="/usr/bin/ffmpeg",
            ffprobe_path="/usr/bin/ffprobe",
            temp_dir=temp_dir,
            use_docker=True,
            docker_image="custom/ffmpeg:latest",
            gpu_enabled=True
        )
        assert proc.ffmpeg_path == "/usr/bin/ffmpeg"
        assert proc.docker_image == "custom/ffmpeg:latest"
        assert proc.use_docker


# ============================================================================
# Test Metadata Extraction
# ============================================================================

class TestMetadataExtraction:
    """Test video metadata extraction."""
    
    def test_get_metadata_success(self, processor, sample_video):
        """Test successful metadata extraction."""
        metadata = processor.get_metadata(sample_video)
        
        assert isinstance(metadata, VideoMetadata)
        assert metadata.filename == "test_video.mp4"
        assert metadata.duration > 0
        assert metadata.width == 640
        assert metadata.height == 480
        assert metadata.fps > 0
        assert metadata.has_video
        assert metadata.file_size > 0
    
    def test_get_metadata_file_not_found(self, processor):
        """Test metadata extraction with missing file."""
        with pytest.raises(RuntimeError):
            processor.get_metadata("/nonexistent/video.mp4")
    
    def test_metadata_structure(self, processor, sample_video):
        """Test metadata structure."""
        metadata = processor.get_metadata(sample_video)
        
        # Check all expected fields
        assert hasattr(metadata, 'filename')
        assert hasattr(metadata, 'duration')
        assert hasattr(metadata, 'width')
        assert hasattr(metadata, 'height')
        assert hasattr(metadata, 'fps')
        assert hasattr(metadata, 'bitrate')
        assert hasattr(metadata, 'codec')
        assert hasattr(metadata, 'has_video')
        assert hasattr(metadata, 'has_audio')
        assert hasattr(metadata, 'extra')


# ============================================================================
# Test Frame Extraction
# ============================================================================

class TestFrameExtraction:
    """Test frame extraction functionality."""
    
    def test_extract_frames_default(self, processor, sample_video, temp_dir):
        """Test basic frame extraction."""
        output_dir = os.path.join(temp_dir, "frames")
        config = ExtractionConfig()
        
        frames = processor.extract_frames(sample_video, output_dir, config)
        
        assert len(frames) > 0
        assert all(isinstance(f, FrameInfo) for f in frames)
        assert all(os.path.exists(f.file_path) for f in frames)
    
    def test_extract_frames_with_fps(self, processor, sample_video, temp_dir):
        """Test frame extraction with specific FPS."""
        output_dir = os.path.join(temp_dir, "frames_fps")
        config = ExtractionConfig(fps=1)
        
        frames = processor.extract_frames(sample_video, output_dir, config)
        
        # 10 second video at 1 fps = ~10 frames
        assert 8 <= len(frames) <= 12
    
    def test_extract_frames_with_time_range(self, processor, sample_video, temp_dir):
        """Test frame extraction with time range."""
        output_dir = os.path.join(temp_dir, "frames_range")
        config = ExtractionConfig(
            fps=1,
            start_time=2.0,
            end_time=5.0
        )
        
        frames = processor.extract_frames(sample_video, output_dir, config)
        
        # 3 second range at 1 fps = ~3 frames
        assert 2 <= len(frames) <= 4
        assert all(f.timestamp >= 2.0 for f in frames)
    
    def test_extract_frames_with_scaling(self, processor, sample_video, temp_dir):
        """Test frame extraction with scaling."""
        output_dir = os.path.join(temp_dir, "frames_scaled")
        config = ExtractionConfig(
            fps=1,
            width=320,
            height=240
        )
        
        frames = processor.extract_frames(sample_video, output_dir, config)
        
        assert len(frames) > 0
        # PIL might not be available in test env


# ============================================================================
# Test Audio Extraction
# ============================================================================

class TestAudioExtraction:
    """Test audio extraction functionality."""
    
    def test_extract_audio_mp3(self, processor, sample_video, temp_dir):
        """Test audio extraction to MP3."""
        output_path = os.path.join(temp_dir, "audio.mp3")
        
        result = processor.extract_audio(
            sample_video,
            output_path,
            format=AudioFormat.MP3,
            bitrate="128k"
        )
        
        assert os.path.exists(output_path)
        assert result['format'] == 'mp3'
        assert result['bitrate'] == '128k'
    
    def test_extract_audio_wav(self, processor, sample_video, temp_dir):
        """Test audio extraction to WAV."""
        output_path = os.path.join(temp_dir, "audio.wav")
        
        result = processor.extract_audio(
            sample_video,
            output_path,
            format=AudioFormat.WAV
        )
        
        assert os.path.exists(output_path)
        assert result['format'] == 'wav'
    
    def test_extract_audio_with_sample_rate(self, processor, sample_video, temp_dir):
        """Test audio extraction with custom sample rate."""
        output_path = os.path.join(temp_dir, "audio_22050.wav")
        
        result = processor.extract_audio(
            sample_video,
            output_path,
            format=AudioFormat.WAV,
            sample_rate=22050
        )
        
        assert os.path.exists(output_path)


# ============================================================================
# Test Scene Detection
# ============================================================================

class TestSceneDetection:
    """Test scene detection functionality."""
    
    def test_detect_scenes(self, processor, sample_video):
        """Test scene detection."""
        scenes = processor.detect_scenes(
            sample_video,
            threshold=0.3,
            min_scene_duration=0.5
        )
        
        assert isinstance(scenes, list)
        # Should detect at least one scene (the whole video)
        assert len(scenes) >= 1
        
        for scene in scenes:
            assert isinstance(scene, SceneInfo)
            assert scene.start_time >= 0
            assert scene.end_time > scene.start_time
    
    def test_detect_scenes_fallback(self, processor, sample_video):
        """Test scene detection fallback."""
        # Force fallback by using high threshold
        scenes = processor._detect_scenes_keyframes(sample_video, min_duration=2.0)
        
        assert isinstance(scenes, list)
        assert len(scenes) >= 1


# ============================================================================
# Test Thumbnail Generation
# ============================================================================

class TestThumbnailGeneration:
    """Test thumbnail generation functionality."""
    
    def test_generate_thumbnail_default(self, processor, sample_video, temp_dir):
        """Test thumbnail at default position (middle)."""
        output_path = os.path.join(temp_dir, "thumb.jpg")
        
        result = processor.generate_thumbnail(sample_video, output_path)
        
        assert os.path.exists(output_path)
        assert result['timestamp'] == 5.0  # Middle of 10s video
    
    def test_generate_thumbnail_at_time(self, processor, sample_video, temp_dir):
        """Test thumbnail at specific time."""
        output_path = os.path.join(temp_dir, "thumb_2s.jpg")
        
        result = processor.generate_thumbnail(sample_video, output_path, time=2.0)
        
        assert os.path.exists(output_path)
        assert result['timestamp'] == 2.0
    
    def test_generate_thumbnail_scaled(self, processor, sample_video, temp_dir):
        """Test thumbnail with scaling."""
        output_path = os.path.join(temp_dir, "thumb_scaled.jpg")
        
        result = processor.generate_thumbnail(
            sample_video,
            output_path,
            width=160,
            height=120
        )
        
        assert os.path.exists(output_path)


# ============================================================================
# Test Format Conversion
# ============================================================================

class TestFormatConversion:
    """Test video format conversion."""
    
    def test_convert_format_same_codec(self, processor, sample_video, temp_dir):
        """Test format conversion with same codecs (copy)."""
        output_path = os.path.join(temp_dir, "converted.mp4")
        
        result = processor.convert_format(
            sample_video,
            output_path,
            video_codec=None,  # Copy
            audio_codec=None
        )
        
        assert os.path.exists(output_path)
        assert result['used_gpu'] is False
    
    def test_convert_format_reencode(self, processor, sample_video, temp_dir):
        """Test format conversion with re-encoding."""
        output_path = os.path.join(temp_dir, "converted.mkv")
        
        result = processor.convert_format(
            sample_video,
            output_path,
            video_codec="h264",
            audio_codec="aac"
        )
        
        assert os.path.exists(output_path)
    
    def test_convert_format_with_crf(self, processor, sample_video, temp_dir):
        """Test format conversion with CRF setting."""
        output_path = os.path.join(temp_dir, "converted_crf23.mp4")
        
        result = processor.convert_format(
            sample_video,
            output_path,
            video_codec="h264",
            crf=23,
            preset="fast"
        )
        
        assert os.path.exists(output_path)


# ============================================================================
# Test Clip Extraction
# ============================================================================

class TestClipExtraction:
    """Test clip extraction functionality."""
    
    def test_extract_clip_reencode(self, processor, sample_video, temp_dir):
        """Test clip extraction with re-encoding."""
        output_path = os.path.join(temp_dir, "clip.mp4")
        
        result = processor.extract_clip(
            sample_video,
            output_path,
            start_time=2.0,
            end_time=5.0,
            reencode=True
        )
        
        assert os.path.exists(output_path)
        assert abs(result['duration'] - 3.0) < 0.1
    
    def test_extract_clip_copy(self, processor, sample_video, temp_dir):
        """Test clip extraction with stream copy."""
        output_path = os.path.join(temp_dir, "clip_copy.mp4")
        
        result = processor.extract_clip(
            sample_video,
            output_path,
            start_time=1.0,
            end_time=4.0,
            reencode=False
        )
        
        assert os.path.exists(output_path)


# ============================================================================
# Test Video Summarization
# ============================================================================

class TestVideoSummarization:
    """Test video summarization functionality."""
    
    def test_summarize_video_default(self, processor, sample_video, temp_dir):
        """Test video summarization with default settings."""
        output_dir = os.path.join(temp_dir, "summary")
        
        result = processor.summarize_video(
            sample_video,
            output_dir,
            num_keyframes=3,
            include_scenes=True
        )
        
        assert result['num_keyframes'] == 3
        assert len(result['keyframes']) == 3
        
        for kf in result['keyframes']:
            assert os.path.exists(kf['file_path'])
            assert 'timestamp' in kf
            assert 'scene_start' in kf
    
    def test_summarize_video_no_scenes(self, processor, sample_video, temp_dir):
        """Test video summarization without scene detection."""
        output_dir = os.path.join(temp_dir, "summary_uniform")
        
        result = processor.summarize_video(
            sample_video,
            output_dir,
            num_keyframes=5,
            include_scenes=False
        )
        
        assert result['num_keyframes'] == 5


# ============================================================================
# Test Batch Processing
# ============================================================================

class TestBatchProcessing:
    """Test batch processing functionality."""
    
    def test_batch_extract_frames(self, processor, sample_video, temp_dir):
        """Test batch frame extraction."""
        results = processor.batch_process(
            [sample_video],
            "extract_frames",
            temp_dir
        )
        
        assert len(results) == 1
        assert results[0]['success']
        assert results[0]['frames_extracted'] > 0
    
    def test_batch_metadata(self, processor, sample_video, temp_dir):
        """Test batch metadata extraction."""
        results = processor.batch_process(
            [sample_video, sample_video],
            "metadata",
            temp_dir
        )
        
        assert len(results) == 2
        assert all(r['success'] for r in results)
        assert all('metadata' in r for r in results)
    
    def test_batch_thumbnail(self, processor, sample_video, temp_dir):
        """Test batch thumbnail generation."""
        results = processor.batch_process(
            [sample_video],
            "thumbnail",
            temp_dir
        )
        
        assert len(results) == 1
        assert results[0]['success']
        assert os.path.exists(results[0]['output_path'])
    
    def test_batch_with_error(self, processor, sample_video, temp_dir):
        """Test batch processing with one invalid file."""
        results = processor.batch_process(
            [sample_video, "/nonexistent/video.mp4"],
            "metadata",
            temp_dir
        )
        
        assert len(results) == 2
        assert results[0]['success']
        assert not results[1]['success']


# ============================================================================
# Test GPU Acceleration
# ============================================================================

class TestGPUAcceleration:
    """Test GPU acceleration detection."""
    
    def test_gpu_detection_none(self, temp_dir):
        """Test GPU detection when no GPU available."""
        proc = VideoProcessor(
            temp_dir=temp_dir,
            gpu_enabled=False
        )
        
        gpu_type = proc._get_gpu_type()
        assert gpu_type == GPUAccelType.NONE
    
    def test_gpu_encoder_fallback(self, temp_dir):
        """Test GPU encoder fallback."""
        proc = VideoProcessor(
            temp_dir=temp_dir,
            gpu_enabled=False
        )
        
        encoder = proc._get_gpu_encoder("h264")
        assert encoder == "libx264"  # Software fallback
    
    @patch('subprocess.run')
    def test_gpu_detection_cuda(self, mock_run, temp_dir):
        """Test CUDA GPU detection."""
        mock_run.return_value = Mock(returncode=0)
        
        proc = VideoProcessor(
            temp_dir=temp_dir,
            gpu_enabled=True
        )
        
        # Force re-check
        proc._gpu_available = None
        
        gpu_type = proc._get_gpu_type()
        assert gpu_type == GPUAccelType.CUDA


# ============================================================================
# Test Docker Support
# ============================================================================

class TestDockerSupport:
    """Test Docker containerization support."""
    
    def test_docker_command_building(self, temp_dir):
        """Test Docker command generation."""
        proc = VideoProcessor(
            temp_dir=temp_dir,
            use_docker=True,
            docker_image="test/ffmpeg:latest"
        )
        
        with patch.object(proc, '_check_docker'):
            cmd = proc._get_ffmpeg_cmd()
            
            assert cmd[0] == "docker"
            assert "run" in cmd
            assert "test/ffmpeg:latest" in cmd
            assert "ffmpeg" in cmd
    
    def test_docker_command_with_gpu(self, temp_dir):
        """Test Docker command with GPU support."""
        proc = VideoProcessor(
            temp_dir=temp_dir,
            use_docker=True,
            gpu_enabled=True
        )
        
        with patch.object(proc, '_check_docker'):
            with patch.object(proc, '_get_gpu_type', return_value=GPUAccelType.CUDA):
                cmd = proc._get_ffmpeg_cmd()
                
                assert "--gpus" in cmd
                assert "all" in cmd


# ============================================================================
# Test Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience wrapper functions."""
    
    def test_create_processor(self, temp_dir):
        """Test create_processor factory."""
        proc = create_processor(temp_dir=temp_dir)
        assert isinstance(proc, VideoProcessor)
    
    def test_quick_metadata(self, sample_video):
        """Test quick_metadata function."""
        metadata = quick_metadata(sample_video)
        assert isinstance(metadata, VideoMetadata)
        assert metadata.duration > 0
    
    def test_quick_thumbnail(self, sample_video, temp_dir):
        """Test quick_thumbnail function."""
        output_path = os.path.join(temp_dir, "quick_thumb.jpg")
        result = quick_thumbnail(sample_video, output_path)
        
        assert os.path.exists(output_path)
        assert 'timestamp' in result


# ============================================================================
# Test Data Classes
# ============================================================================

class TestDataClasses:
    """Test data class structures."""
    
    def test_video_metadata_defaults(self):
        """Test VideoMetadata defaults."""
        meta = VideoMetadata(filename="test.mp4")
        assert meta.filename == "test.mp4"
        assert meta.duration == 0.0
        assert meta.width == 0
        assert meta.height == 0
        assert meta.has_video is True
        assert meta.has_audio is False
    
    def test_extraction_config_defaults(self):
        """Test ExtractionConfig defaults."""
        config = ExtractionConfig()
        assert config.output_format == ImageFormat.JPG
        assert config.quality == 95
        assert config.maintain_aspect is True
        assert config.use_gpu is False
    
    def test_frame_info_creation(self):
        """Test FrameInfo creation."""
        frame = FrameInfo(
            frame_number=10,
            timestamp=0.333,
            file_path="/tmp/frame_010.jpg"
        )
        assert frame.frame_number == 10
        assert frame.timestamp == 0.333


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring full FFmpeg installation."""
    
    def test_full_workflow(self, temp_dir):
        """Test complete video processing workflow."""
        # Create sample video
        video_path = os.path.join(temp_dir, "workflow_test.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=5:size=1280x720:rate=24",
            "-f", "lavfi",
            "-i", "sine=frequency=1000:duration=5",
            "-pix_fmt", "yuv420p",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            pytest.skip("FFmpeg not available")
        
        processor = VideoProcessor(temp_dir=temp_dir)
        
        # 1. Extract metadata
        metadata = processor.get_metadata(video_path)
        assert metadata.width == 1280
        
        # 2. Generate thumbnail
        thumb_path = os.path.join(temp_dir, "thumb.jpg")
        processor.generate_thumbnail(video_path, thumb_path)
        assert os.path.exists(thumb_path)
        
        # 3. Extract frames
        frames_dir = os.path.join(temp_dir, "frames")
        config = ExtractionConfig(fps=1)
        frames = processor.extract_frames(video_path, frames_dir, config)
        assert len(frames) == 5  # 5 seconds at 1 fps
        
        # 4. Extract audio
        audio_path = os.path.join(temp_dir, "audio.wav")
        processor.extract_audio(video_path, audio_path, format=AudioFormat.WAV)
        assert os.path.exists(audio_path)
        
        # 5. Extract clip
        clip_path = os.path.join(temp_dir, "clip.mp4")
        processor.extract_clip(video_path, clip_path, 1.0, 3.0)
        assert os.path.exists(clip_path)
        
        # 6. Detect scenes
        scenes = processor.detect_scenes(video_path)
        assert isinstance(scenes, list)
        
        # 7. Summarize
        summary_dir = os.path.join(temp_dir, "summary")
        summary = processor.summarize_video(video_path, summary_dir, num_keyframes=3)
        assert summary['num_keyframes'] == 3
        
        print("Full workflow test passed!")


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_video_path(self, processor):
        """Test handling of invalid video path."""
        with pytest.raises(RuntimeError):
            processor.get_metadata("/invalid/path/to/video.mp4")
    
    def test_ffmpeg_not_found(self, temp_dir):
        """Test handling when FFmpeg not found."""
        proc = VideoProcessor(
            ffmpeg_path="/nonexistent/ffmpeg",
            temp_dir=temp_dir
        )
        
        with pytest.raises((RuntimeError, FileNotFoundError)):
            proc.get_metadata("test.mp4")
    
    def test_docker_not_available(self, temp_dir):
        """Test handling when Docker not available."""
        proc = VideoProcessor(
            temp_dir=temp_dir,
            use_docker=True
        )
        
        with pytest.raises(RuntimeError):
            proc._check_docker()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Run with: python -m pytest tests/test_skill_video_frames.py -v
    # Or: python tests/test_skill_video_frames.py
    pytest.main([__file__, "-v", "--tb=short"])
