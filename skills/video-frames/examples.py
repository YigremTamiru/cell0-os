#!/usr/bin/env python3
"""
Video Frames Skill - Examples
Cell 0 OS - Video Analysis via FFmpeg

This script demonstrates all the capabilities of the Video Frames Skill.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.video_frames import (
    VideoProcessor,
    ExtractionConfig,
    ImageFormat,
    AudioFormat
)


def example_metadata(processor, video_path):
    """Example: Extract video metadata."""
    print("\n" + "="*60)
    print("Example: Extract Video Metadata")
    print("="*60)
    
    metadata = processor.get_metadata(video_path)
    
    print(f"Filename: {metadata.filename}")
    print(f"Duration: {metadata.duration:.2f} seconds")
    print(f"Resolution: {metadata.width}x{metadata.height}")
    print(f"FPS: {metadata.fps:.2f}")
    print(f"Video Codec: {metadata.codec}")
    print(f"Audio Codec: {metadata.audio_codec}")
    print(f"File Size: {metadata.file_size / 1024 / 1024:.2f} MB")
    print(f"Has Audio: {metadata.has_audio}")
    print(f"Has Video: {metadata.has_video}")


def example_extract_frames(processor, video_path, output_dir):
    """Example: Extract frames from video."""
    print("\n" + "="*60)
    print("Example: Extract Frames")
    print("="*60)
    
    # Create output directory
    frames_dir = os.path.join(output_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    # Extract 1 frame per second
    config = ExtractionConfig(
        output_format=ImageFormat.JPG,
        quality=95,
        fps=1.0
    )
    
    frames = processor.extract_frames(video_path, frames_dir, config)
    
    print(f"Extracted {len(frames)} frames to {frames_dir}")
    print(f"First frame: {frames[0].file_path}")
    print(f"Last frame: {frames[-1].file_path}")


def example_extract_audio(processor, video_path, output_dir):
    """Example: Extract audio from video."""
    print("\n" + "="*60)
    print("Example: Extract Audio")
    print("="*60)
    
    output_path = os.path.join(output_dir, "audio.mp3")
    
    result = processor.extract_audio(
        video_path,
        output_path,
        format=AudioFormat.MP3,
        bitrate="192k"
    )
    
    print(f"Audio extracted to: {result['output_path']}")
    print(f"Format: {result['format']}")
    print(f"Bitrate: {result['bitrate']}")


def example_scene_detection(processor, video_path):
    """Example: Detect scene changes."""
    print("\n" + "="*60)
    print("Example: Scene Detection")
    print("="*60)
    
    scenes = processor.detect_scenes(
        video_path,
        threshold=0.3,
        min_scene_duration=0.5
    )
    
    print(f"Detected {len(scenes)} scenes:")
    for i, scene in enumerate(scenes[:5]):  # Show first 5
        duration = scene.end_time - scene.start_time
        print(f"  Scene {i+1}: {scene.start_time:.2f}s - {scene.end_time:.2f}s (duration: {duration:.2f}s)")
    
    if len(scenes) > 5:
        print(f"  ... and {len(scenes) - 5} more scenes")


def example_thumbnail(processor, video_path, output_dir):
    """Example: Generate thumbnail."""
    print("\n" + "="*60)
    print("Example: Generate Thumbnail")
    print("="*60)
    
    output_path = os.path.join(output_dir, "thumbnail.jpg")
    
    result = processor.generate_thumbnail(
        video_path,
        output_path,
        time=None,  # Middle of video
        width=320,
        height=180,
        quality=90
    )
    
    print(f"Thumbnail generated: {result['output_path']}")
    print(f"Timestamp: {result['timestamp']:.2f}s")


def example_convert_format(processor, video_path, output_dir):
    """Example: Convert video format."""
    print("\n" + "="*60)
    print("Example: Format Conversion")
    print("="*60)
    
    output_path = os.path.join(output_dir, "converted.mkv")
    
    result = processor.convert_format(
        video_path,
        output_path,
        video_codec="h264",
        audio_codec="aac",
        preset="fast",
        crf=23
    )
    
    print(f"Video converted to: {result['output_path']}")
    print(f"Video Codec: {result['video_codec']}")
    print(f"Audio Codec: {result['audio_codec']}")
    print(f"GPU Used: {result['used_gpu']}")


def example_extract_clip(processor, video_path, output_dir):
    """Example: Extract video clip."""
    print("\n" + "="*60)
    print("Example: Extract Clip")
    print("="*60)
    
    output_path = os.path.join(output_dir, "clip.mp4")
    
    result = processor.extract_clip(
        video_path,
        output_path,
        start_time=2.0,
        end_time=5.0,
        reencode=True
    )
    
    print(f"Clip extracted to: {result['output_path']}")
    print(f"Start: {result['start_time']:.2f}s")
    print(f"End: {result['end_time']:.2f}s")
    print(f"Duration: {result['duration']:.2f}s")


def example_summarize(processor, video_path, output_dir):
    """Example: Summarize video."""
    print("\n" + "="*60)
    print("Example: Video Summarization")
    print("="*60)
    
    summary_dir = os.path.join(output_dir, "summary")
    
    result = processor.summarize_video(
        video_path,
        summary_dir,
        num_keyframes=5,
        include_scenes=True
    )
    
    print(f"Video duration: {result['duration']:.2f}s")
    print(f"Scenes detected: {result['scenes_detected']}")
    print(f"Keyframes extracted: {result['num_keyframes']}")
    print("\nKeyframes:")
    for kf in result['keyframes']:
        print(f"  Frame {kf['frame_number']}: {kf['timestamp']:.2f}s -> {kf['file_path']}")


def example_batch_process(processor, video_paths, output_dir):
    """Example: Batch processing."""
    print("\n" + "="*60)
    print("Example: Batch Processing")
    print("="*60)
    
    results = processor.batch_process(
        video_paths,
        "metadata",
        output_dir
    )
    
    print(f"Processed {len(results)} videos:")
    for result in results:
        if result['success']:
            meta = result.get('metadata', {})
            print(f"  ✓ {result['input']}: {meta.get('duration', 0):.2f}s")
        else:
            print(f"  ✗ {result['input']}: {result.get('error', 'Unknown error')}")


def create_test_video(output_path, duration=10):
    """Create a test video using FFmpeg."""
    import subprocess
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size=640x480:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration}",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Video Frames Skill Examples"
    )
    parser.add_argument(
        "--video",
        help="Path to input video file"
    )
    parser.add_argument(
        "--output",
        default="./output",
        help="Output directory for results"
    )
    parser.add_argument(
        "--example",
        choices=[
            "all", "metadata", "frames", "audio",
            "scenes", "thumbnail", "convert", "clip",
            "summarize", "batch"
        ],
        default="all",
        help="Which example to run"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Enable GPU acceleration"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Create test video if no input provided
    if args.video:
        video_path = args.video
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            return 1
    else:
        print("No video provided. Creating test video...")
        video_path = os.path.join(args.output, "test_video.mp4")
        if not create_test_video(video_path):
            print("Error: Could not create test video. Is FFmpeg installed?")
            return 1
        print(f"Test video created: {video_path}")
    
    # Create processor
    processor = VideoProcessor(gpu_enabled=args.gpu)
    
    # Run examples
    examples_to_run = {
        "metadata": example_metadata,
        "frames": example_extract_frames,
        "audio": example_extract_audio,
        "scenes": example_scene_detection,
        "thumbnail": example_thumbnail,
        "convert": example_convert_format,
        "clip": example_extract_clip,
        "summarize": example_summarize,
        "batch": example_batch_process
    }
    
    try:
        if args.example == "all":
            # Run all examples except batch (needs multiple videos)
            for name, func in examples_to_run.items():
                if name == "batch":
                    func(processor, [video_path], args.output)
                else:
                    func(processor, video_path, args.output)
        else:
            func = examples_to_run[args.example]
            if args.example == "batch":
                func(processor, [video_path], args.output)
            else:
                func(processor, video_path, args.output)
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print(f"Output directory: {os.path.abspath(args.output)}")
        print("="*60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
