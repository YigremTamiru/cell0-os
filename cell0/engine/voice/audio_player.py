"""
Audio Player Module for Cell 0 OS
Cross-platform audio playback with streaming support
"""

import asyncio
import io
import logging
import platform
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import aiofiles

logger = logging.getLogger(__name__)


class BaseAudioPlayer(ABC):
    """Abstract base class for audio players"""
    
    @abstractmethod
    async def play_file(self, file_path: Path) -> None:
        """Play audio file"""
        pass
    
    @abstractmethod
    async def play_buffer(self, audio_buffer: bytes) -> None:
        """Play audio from buffer"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop playback"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if player is available"""
        pass


class MacOSAudioPlayer(BaseAudioPlayer):
    """macOS audio player using afplay"""
    
    def __init__(self):
        self._current_proc: Optional[asyncio.subprocess.Process] = None
    
    def is_available(self) -> bool:
        return platform.system() == "Darwin"
    
    async def play_file(self, file_path: Path) -> None:
        """Play audio file using afplay"""
        await self.stop()  # Stop any current playback
        
        cmd = ["afplay", str(file_path)]
        
        self._current_proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        
        await self._current_proc.wait()
        self._current_proc = None
    
    async def play_buffer(self, audio_buffer: bytes) -> None:
        """Play audio buffer by saving to temp file"""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_buffer)
            tmp_path = Path(tmp.name)
        
        try:
            await self.play_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    async def stop(self) -> None:
        """Stop current playback"""
        if self._current_proc and self._current_proc.returncode is None:
            self._current_proc.terminate()
            try:
                await asyncio.wait_for(self._current_proc.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self._current_proc.kill()


class LinuxAudioPlayer(BaseAudioPlayer):
    """Linux audio player using aplay or paplay"""
    
    def __init__(self):
        self._current_proc: Optional[asyncio.subprocess.Process] = None
        self._player_cmd = self._detect_player()
    
    def _detect_player(self) -> Optional[str]:
        """Detect available audio player"""
        players = ["paplay", "aplay", "mpg123", "ffplay"]
        
        for player in players:
            try:
                result = subprocess.run(
                    ["which", player],
                    capture_output=True,
                    check=True
                )
                return player
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        return None
    
    def is_available(self) -> bool:
        return self._player_cmd is not None
    
    async def play_file(self, file_path: Path) -> None:
        """Play audio file"""
        if not self._player_cmd:
            raise RuntimeError("No audio player available")
        
        await self.stop()
        
        cmd = [self._player_cmd, str(file_path)]
        
        if self._player_cmd == "ffplay":
            cmd = ["ffplay", "-nodisp", "-autoexit", str(file_path)]
        
        self._current_proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        
        await self._current_proc.wait()
        self._current_proc = None
    
    async def play_buffer(self, audio_buffer: bytes) -> None:
        """Play audio buffer"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_buffer)
            tmp_path = Path(tmp.name)
        
        try:
            await self.play_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    async def stop(self) -> None:
        """Stop playback"""
        if self._current_proc and self._current_proc.returncode is None:
            self._current_proc.terminate()
            try:
                await asyncio.wait_for(self._current_proc.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self._current_proc.kill()


class PyAudioPlayer(BaseAudioPlayer):
    """Python PyAudio-based player for lower latency"""
    
    def __init__(self):
        self._pyaudio = None
        self._stream = None
    
    def is_available(self) -> bool:
        try:
            import pyaudio
            return True
        except ImportError:
            return False
    
    async def play_file(self, file_path: Path) -> None:
        """Play audio file using PyAudio"""
        import wave
        
        # Run in thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._play_file_sync, file_path)
    
    def _play_file_sync(self, file_path: Path):
        """Synchronous file playback"""
        import pyaudio
        import wave
        
        wf = wave.open(str(file_path), 'rb')
        
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        
        chunk = 1024
        data = wf.readframes(chunk)
        
        while data:
            stream.write(data)
            data = wf.readframes(chunk)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf.close()
    
    async def play_buffer(self, audio_buffer: bytes) -> None:
        """Play audio buffer"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_buffer)
            tmp_path = Path(tmp.name)
        
        try:
            await self.play_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    async def stop(self) -> None:
        """Stop playback"""
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None


class AudioPlayer:
    """Cross-platform audio player with automatic backend selection"""
    
    def __init__(self):
        self._player: Optional[BaseAudioPlayer] = None
        self._select_player()
    
    def _select_player(self):
        """Select best available player"""
        # Try platform-specific players first
        if platform.system() == "Darwin":
            player = MacOSAudioPlayer()
            if player.is_available():
                self._player = player
                logger.info("Using macOS afplay audio player")
                return
        
        elif platform.system() == "Linux":
            player = LinuxAudioPlayer()
            if player.is_available():
                self._player = player
                logger.info(f"Using Linux {player._player_cmd} audio player")
                return
        
        # Try PyAudio
        player = PyAudioPlayer()
        if player.is_available():
            self._player = player
            logger.info("Using PyAudio player")
            return
        
        raise RuntimeError("No audio player available")
    
    async def play_file(self, file_path: Path) -> None:
        """Play audio file"""
        await self._player.play_file(file_path)
    
    async def play_buffer(self, audio_buffer: bytes) -> None:
        """Play audio buffer"""
        await self._player.play_buffer(audio_buffer)
    
    async def stop(self) -> None:
        """Stop playback"""
        await self._player.stop()
