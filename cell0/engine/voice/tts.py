"""
Text-to-Speech Module for Cell 0 OS
Provides TTS capabilities using ElevenLabs API (primary) and macOS say (fallback)
"""

import asyncio
import io
import os
import platform
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, AsyncIterator, Callable
import logging

import aiohttp
import aiofiles

logger = logging.getLogger(__name__)


class TTSProvider(Enum):
    """TTS provider enumeration"""
    ELEVENLABS = "elevenlabs"
    MACOS_SAY = "macos_say"
    LINUX_ESPEAK = "espeak"


@dataclass
class TTSConfig:
    """Configuration for TTS"""
    provider: TTSProvider = TTSProvider.ELEVENLABS
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice (Rachel)
    model_id: str = "eleven_monolingual_v1"
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    # macOS say options
    voice: str = "Samantha"
    rate: int = 175  # Words per minute
    # Streaming
    enable_streaming: bool = True
    chunk_size: int = 8192


class BaseTTS(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> Path:
        """Synthesize text to speech"""
        pass
    
    @abstractmethod
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Stream synthesized audio chunks"""
        pass
    
    @abstractmethod
    async def play(self, text: str) -> None:
        """Synthesize and play text immediately"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available on this system"""
        pass


class ElevenLabsTTS(BaseTTS):
    """ElevenLabs API TTS provider"""
    
    API_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(self, config: TTSConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or self._get_api_key()
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _get_api_key(self) -> str:
        """Get API key from 1Password or environment"""
        # Try environment variable first
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if api_key:
            return api_key
        
        # Try 1Password CLI
        try:
            result = subprocess.run(
                ["op", "read", "op://Private/ElevenLabs/credential"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        raise ValueError("ElevenLabs API key not found in environment or 1Password")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"xi-api-key": self.api_key}
            )
        return self.session
    
    def is_available(self) -> bool:
        """Check if API key is available"""
        try:
            return bool(self.api_key)
        except ValueError:
            return False
    
    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> Path:
        """Synthesize text to audio file"""
        session = await self._get_session()
        
        url = f"{self.API_URL}/text-to-speech/{self.config.voice_id}"
        
        payload = {
            "text": text,
            "model_id": self.config.model_id,
            "voice_settings": {
                "stability": self.config.stability,
                "similarity_boost": self.config.similarity_boost,
                "style": self.config.style,
                "use_speaker_boost": self.config.use_speaker_boost
            }
        }
        
        async with session.post(url, json=payload) as response:
            response.raise_for_status()
            audio_data = await response.read()
        
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".mp3"))
        
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(audio_data)
        
        logger.info(f"Synthesized audio saved to {output_path}")
        return output_path
    
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Stream synthesized audio from ElevenLabs"""
        session = await self._get_session()
        
        url = f"{self.API_URL}/text-to-speech/{self.config.voice_id}/stream"
        
        payload = {
            "text": text,
            "model_id": self.config.model_id,
            "voice_settings": {
                "stability": self.config.stability,
                "similarity_boost": self.config.similarity_boost,
                "style": self.config.style,
                "use_speaker_boost": self.config.use_speaker_boost
            }
        }
        
        async with session.post(url, json=payload) as response:
            response.raise_for_status()
            
            while True:
                chunk = await response.content.read(self.config.chunk_size)
                if not chunk:
                    break
                yield chunk
    
    async def play(self, text: str) -> None:
        """Synthesize and play text immediately using streaming"""
        from .audio_player import AudioPlayer
        
        player = AudioPlayer()
        audio_buffer = io.BytesIO()
        
        async for chunk in self.synthesize_stream(text):
            audio_buffer.write(chunk)
        
        audio_buffer.seek(0)
        await player.play_buffer(audio_buffer.read())
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


class MacOSSayTTS(BaseTTS):
    """macOS say command TTS provider"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        
    def is_available(self) -> bool:
        """Check if running on macOS"""
        return platform.system() == "Darwin"
    
    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> Path:
        """Synthesize text to audio file (AIFF format)"""
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".aiff"))
        
        cmd = [
            "say",
            "-v", self.config.voice,
            "-r", str(self.config.rate),
            "-o", str(output_path),
            text
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"say command failed: {stderr.decode()}")
        
        logger.info(f"Synthesized audio saved to {output_path}")
        return output_path
    
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Streaming not supported for macOS say - synthesize to temp file then stream"""
        output_path = await self.synthesize(text)
        
        async with aiofiles.open(output_path, "rb") as f:
            while True:
                chunk = await f.read(self.config.chunk_size)
                if not chunk:
                    break
                yield chunk
        
        # Cleanup temp file
        output_path.unlink(missing_ok=True)
    
    async def play(self, text: str) -> None:
        """Play text using say command"""
        cmd = [
            "say",
            "-v", self.config.voice,
            "-r", str(self.config.rate),
            text
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await proc.wait()


class LinuxEspeakTTS(BaseTTS):
    """Linux espeak TTS provider (fallback)"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        
    def is_available(self) -> bool:
        """Check if espeak is available"""
        if platform.system() != "Linux":
            return False
        try:
            subprocess.run(["which", "espeak"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> Path:
        """Synthesize text to WAV file using espeak"""
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".wav"))
        
        cmd = [
            "espeak",
            "-v", self.config.voice,
            "-s", str(self.config.rate),
            "-w", str(output_path),
            text
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"espeak command failed: {stderr.decode()}")
        
        return output_path
    
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Streaming not directly supported - synthesize to temp file then stream"""
        output_path = await self.synthesize(text)
        
        async with aiofiles.open(output_path, "rb") as f:
            while True:
                chunk = await f.read(self.config.chunk_size)
                if not chunk:
                    break
                yield chunk
        
        output_path.unlink(missing_ok=True)
    
    async def play(self, text: str) -> None:
        """Play text using espeak"""
        cmd = [
            "espeak",
            "-v", self.config.voice,
            "-s", str(self.config.rate),
            text
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await proc.wait()


class TTSManager:
    """Manager for TTS with automatic fallback"""
    
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self.providers: dict[TTSProvider, BaseTTS] = {}
        self._current_provider: Optional[BaseTTS] = None
        
    def _initialize_providers(self):
        """Initialize all available TTS providers"""
        # Try ElevenLabs first
        try:
            elevenlabs = ElevenLabsTTS(self.config)
            if elevenlabs.is_available():
                self.providers[TTSProvider.ELEVENLABS] = elevenlabs
                logger.info("ElevenLabs TTS initialized")
        except ValueError as e:
            logger.warning(f"ElevenLabs not available: {e}")
        
        # macOS say
        macos_say = MacOSSayTTS(self.config)
        if macos_say.is_available():
            self.providers[TTSProvider.MACOS_SAY] = macos_say
            logger.info("macOS say TTS initialized")
        
        # Linux espeak
        linux_espeak = LinuxEspeakTTS(self.config)
        if linux_espeak.is_available():
            self.providers[TTSProvider.LINUX_ESPEAK] = linux_espeak
            logger.info("Linux espeak TTS initialized")
        
        # Select primary provider based on preference
        preferred_order = [
            TTSProvider.ELEVENLABS,
            TTSProvider.MACOS_SAY,
            TTSProvider.LINUX_ESPEAK
        ]
        
        for provider in preferred_order:
            if provider in self.providers:
                self._current_provider = self.providers[provider]
                logger.info(f"Using TTS provider: {provider.value}")
                break
        
        if not self._current_provider:
            raise RuntimeError("No TTS provider available")
    
    @property
    def current_provider(self) -> BaseTTS:
        """Get current TTS provider"""
        if self._current_provider is None:
            self._initialize_providers()
        return self._current_provider
    
    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> Path:
        """Synthesize text using current provider"""
        return await self.current_provider.synthesize(text, output_path)
    
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Stream synthesized audio"""
        async for chunk in self.current_provider.synthesize_stream(text):
            yield chunk
    
    async def play(self, text: str) -> None:
        """Play text immediately"""
        await self.current_provider.play(text)
    
    def switch_provider(self, provider: TTSProvider) -> bool:
        """Switch to a specific provider"""
        if provider in self.providers:
            self._current_provider = self.providers[provider]
            logger.info(f"Switched to TTS provider: {provider.value}")
            return True
        return False
    
    def list_available_providers(self) -> list[TTSProvider]:
        """List all available TTS providers"""
        if not self.providers:
            self._initialize_providers()
        return list(self.providers.keys())
    
    async def close(self):
        """Close all providers"""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()


# Convenience function
async def speak(text: str, voice: Optional[str] = None) -> None:
    """Quick speak function using default configuration"""
    config = TTSConfig()
    if voice:
        config.voice_id = voice
    
    manager = TTSManager(config)
    try:
        await manager.play(text)
    finally:
        await manager.close()
