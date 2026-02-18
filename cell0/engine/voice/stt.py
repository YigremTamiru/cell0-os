"""
Speech-to-Text Module for Cell 0 OS
Provides STT capabilities using OpenAI Whisper API or local whisper.cpp
"""

import asyncio
import io
import json
import os
import subprocess
import tempfile
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, AsyncIterator, Callable, BinaryIO
import logging

import aiohttp
import aiofiles
import numpy as np

logger = logging.getLogger(__name__)


class STTProvider(Enum):
    """STT provider enumeration"""
    WHISPER_API = "whisper_api"
    WHISPER_CPP = "whisper_cpp"
    WHISPER_LOCAL = "whisper_local"  # Python whisper package


@dataclass
class STTConfig:
    """Configuration for STT"""
    provider: STTProvider = STTProvider.WHISPER_API
    model_size: str = "base"  # tiny, base, small, medium, large
    language: Optional[str] = None  # Auto-detect if None
    temperature: float = 0.0
    # API options
    api_base: str = "https://api.openai.com/v1"
    # whisper.cpp options
    whisper_cpp_path: Optional[Path] = None
    whisper_model_path: Optional[Path] = None
    n_threads: int = 4
    # Streaming
    enable_streaming: bool = True
    stream_chunk_ms: int = 100  # Milliseconds per chunk
    # VAD
    enable_vad: bool = True
    vad_threshold: float = 0.5
    silence_duration_ms: int = 1000


@dataclass
class TranscriptionResult:
    """Result from STT transcription"""
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    segments: Optional[list] = None
    duration_ms: Optional[float] = None


class BaseSTT(ABC):
    """Abstract base class for STT providers"""
    
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe audio file to text"""
        pass
    
    @abstractmethod
    async def transcribe_buffer(self, audio_buffer: bytes) -> TranscriptionResult:
        """Transcribe audio buffer to text"""
        pass
    
    @abstractmethod
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> TranscriptionResult:
        """Transcribe streaming audio"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class WhisperAPISTT(BaseSTT):
    """OpenAI Whisper API STT provider"""
    
    def __init__(self, config: STTConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or self._get_api_key()
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _get_api_key(self) -> str:
        """Get API key from 1Password or environment"""
        # Try environment variable first
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # Try 1Password CLI
        try:
            result = subprocess.run(
                ["op", "read", "op://Private/OpenAI/credential"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        raise ValueError("OpenAI API key not found in environment or 1Password")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self.session
    
    def is_available(self) -> bool:
        """Check if API key is available"""
        try:
            return bool(self.api_key)
        except ValueError:
            return False
    
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe audio file using Whisper API"""
        session = await self._get_session()
        
        url = f"{self.config.api_base}/audio/transcriptions"
        
        data = aiohttp.FormData()
        data.add_field("model", "whisper-1")
        data.add_field("language", self.config.language or "")
        data.add_field("temperature", str(self.config.temperature))
        
        async with aiofiles.open(audio_path, "rb") as f:
            audio_data = await f.read()
            data.add_field("file", audio_data, filename=audio_path.name)
        
        async with session.post(url, data=data) as response:
            response.raise_for_status()
            result = await response.json()
        
        return TranscriptionResult(
            text=result.get("text", ""),
            language=result.get("language"),
            segments=result.get("segments")
        )
    
    async def transcribe_buffer(self, audio_buffer: bytes) -> TranscriptionResult:
        """Transcribe audio buffer"""
        # Save buffer to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_buffer)
            tmp_path = Path(tmp.name)
        
        try:
            return await self.transcribe(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> TranscriptionResult:
        """Transcribe streaming audio - buffers and transcribes"""
        # Collect all chunks
        buffer = io.BytesIO()
        async for chunk in audio_stream:
            buffer.write(chunk)
        
        return await self.transcribe_buffer(buffer.getvalue())
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


class WhisperCppSTT(BaseSTT):
    """Local whisper.cpp STT provider"""
    
    def __init__(self, config: STTConfig):
        self.config = config
        self.executable = config.whisper_cpp_path or self._find_whisper_cpp()
        self.model_path = config.whisper_model_path or self._find_model()
        
    def _find_whisper_cpp(self) -> Optional[Path]:
        """Find whisper.cpp executable"""
        possible_paths = [
            Path.home() / ".local" / "bin" / "whisper-cli",
            Path.home() / "whisper.cpp" / "main",
            Path.home() / "whisper.cpp" / "whisper-cli",
            Path("/usr/local/bin/whisper-cli"),
            Path("/opt/whisper.cpp/whisper-cli"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Try which command
        try:
            result = subprocess.run(
                ["which", "whisper-cli"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except FileNotFoundError:
            pass
        
        return None
    
    def _find_model(self) -> Optional[Path]:
        """Find whisper model file"""
        model_name = f"ggml-{self.config.model_size}.bin"
        possible_paths = [
            Path.home() / "whisper.cpp" / "models" / model_name,
            Path.home() / ".local" / "share" / "whisper" / "models" / model_name,
            Path("/usr/local/share/whisper/models") / model_name,
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def is_available(self) -> bool:
        """Check if whisper.cpp is available"""
        return self.executable is not None and self.model_path is not None
    
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using whisper.cpp"""
        if not self.is_available():
            raise RuntimeError("whisper.cpp not available")
        
        # whisper.cpp requires 16kHz WAV
        converted_path = await self._ensure_16khz_wav(audio_path)
        
        cmd = [
            str(self.executable),
            "-m", str(self.model_path),
            "-f", str(converted_path),
            "-nt",  # No timestamps
            "--output-json",
            "-t", str(self.config.n_threads),
        ]
        
        if self.config.language:
            cmd.extend(["-l", self.config.language])
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"whisper.cpp failed: {stderr.decode()}")
        
        # Parse output
        output_file = Path(str(converted_path) + ".json")
        if output_file.exists():
            async with aiofiles.open(output_file, "r") as f:
                result_data = json.loads(await f.read())
            output_file.unlink(missing_ok=True)
            
            text = result_data.get("transcription", [{}])[0].get("text", "")
            return TranscriptionResult(
                text=text,
                language=self.config.language
            )
        else:
            # Fallback to stdout parsing
            text = stdout.decode().strip()
            return TranscriptionResult(text=text)
    
    async def _ensure_16khz_wav(self, audio_path: Path) -> Path:
        """Convert audio to 16kHz mono WAV if needed"""
        # Check if already correct format
        try:
            with wave.open(str(audio_path), 'rb') as wav:
                if wav.getframerate() == 16000 and wav.getnchannels() == 1:
                    return audio_path
        except wave.Error:
            pass  # Not a WAV file
        
        # Convert using ffmpeg
        output_path = Path(tempfile.mktemp(suffix=".wav"))
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(output_path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError("Failed to convert audio to 16kHz WAV")
        
        return output_path
    
    async def transcribe_buffer(self, audio_buffer: bytes) -> TranscriptionResult:
        """Transcribe audio buffer"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_buffer)
            tmp_path = Path(tmp.name)
        
        try:
            return await self.transcribe(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> TranscriptionResult:
        """Transcribe streaming audio"""
        buffer = io.BytesIO()
        async for chunk in audio_stream:
            buffer.write(chunk)
        
        return await self.transcribe_buffer(buffer.getvalue())


class WhisperLocalSTT(BaseSTT):
    """Local Python whisper package STT provider"""
    
    def __init__(self, config: STTConfig):
        self.config = config
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load whisper model"""
        try:
            import whisper
            self.model = whisper.load_model(self.config.model_size)
            logger.info(f"Loaded whisper model: {self.config.model_size}")
        except ImportError:
            logger.error("whisper package not installed")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if whisper package is available"""
        return self.model is not None
    
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using local whisper"""
        if not self.is_available():
            raise RuntimeError("whisper package not available")
        
        # Run in thread pool since whisper is CPU-intensive
        loop = asyncio.get_event_loop()
        
        def _transcribe():
            result = self.model.transcribe(
                str(audio_path),
                language=self.config.language,
                temperature=self.config.temperature
            )
            return result
        
        result = await loop.run_in_executor(None, _transcribe)
        
        return TranscriptionResult(
            text=result.get("text", ""),
            language=result.get("language"),
            segments=result.get("segments")
        )
    
    async def transcribe_buffer(self, audio_buffer: bytes) -> TranscriptionResult:
        """Transcribe audio buffer"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_buffer)
            tmp_path = Path(tmp.name)
        
        try:
            return await self.transcribe(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> TranscriptionResult:
        """Transcribe streaming audio"""
        buffer = io.BytesIO()
        async for chunk in audio_stream:
            buffer.write(chunk)
        
        return await self.transcribe_buffer(buffer.getvalue())


class STTManager:
    """Manager for STT with automatic fallback"""
    
    def __init__(self, config: Optional[STTConfig] = None):
        self.config = config or STTConfig()
        self.providers: dict[STTProvider, BaseSTT] = {}
        self._current_provider: Optional[BaseSTT] = None
        
    def _initialize_providers(self):
        """Initialize all available STT providers"""
        # Try API first
        try:
            whisper_api = WhisperAPISTT(self.config)
            if whisper_api.is_available():
                self.providers[STTProvider.WHISPER_API] = whisper_api
                logger.info("Whisper API STT initialized")
        except ValueError as e:
            logger.warning(f"Whisper API not available: {e}")
        
        # Try whisper.cpp
        whisper_cpp = WhisperCppSTT(self.config)
        if whisper_cpp.is_available():
            self.providers[STTProvider.WHISPER_CPP] = whisper_cpp
            logger.info("whisper.cpp STT initialized")
        
        # Try local whisper
        whisper_local = WhisperLocalSTT(self.config)
        if whisper_local.is_available():
            self.providers[STTProvider.WHISPER_LOCAL] = whisper_local
            logger.info("Local whisper STT initialized")
        
        # Select primary provider based on preference
        preferred_order = [
            STTProvider.WHISPER_API,
            STTProvider.WHISPER_CPP,
            STTProvider.WHISPER_LOCAL
        ]
        
        for provider in preferred_order:
            if provider in self.providers:
                self._current_provider = self.providers[provider]
                logger.info(f"Using STT provider: {provider.value}")
                break
        
        if not self._current_provider:
            raise RuntimeError("No STT provider available")
    
    @property
    def current_provider(self) -> BaseSTT:
        """Get current STT provider"""
        if self._current_provider is None:
            self._initialize_providers()
        return self._current_provider
    
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe audio file"""
        return await self.current_provider.transcribe(audio_path)
    
    async def transcribe_buffer(self, audio_buffer: bytes) -> TranscriptionResult:
        """Transcribe audio buffer"""
        return await self.current_provider.transcribe_buffer(audio_buffer)
    
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> TranscriptionResult:
        """Transcribe streaming audio"""
        return await self.current_provider.transcribe_stream(audio_stream)
    
    def switch_provider(self, provider: STTProvider) -> bool:
        """Switch to a specific provider"""
        if provider in self.providers:
            self._current_provider = self.providers[provider]
            logger.info(f"Switched to STT provider: {provider.value}")
            return True
        return False
    
    def list_available_providers(self) -> list[STTProvider]:
        """List all available STT providers"""
        if not self.providers:
            self._initialize_providers()
        return list(self.providers.keys())
    
    async def close(self):
        """Close all providers"""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()
