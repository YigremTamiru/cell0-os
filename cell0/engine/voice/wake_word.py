"""
Wake Word Detection Module for Cell 0 OS
Provides wake word detection using Porcupine or VAD-based detection
"""

import asyncio
import io
import logging
import os
import struct
import subprocess
import tempfile
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, AsyncIterator, List
import platform

import numpy as np

logger = logging.getLogger(__name__)


class WakeWordProvider(Enum):
    """Wake word provider enumeration"""
    PORCUPINE = "porcupine"
    VAD_KEYWORD = "vad_keyword"  # VAD + keyword matching
    OPENWAKEWORD = "openwakeword"


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection"""
    provider: WakeWordProvider = WakeWordProvider.VAD_KEYWORD
    # Porcupine settings
    porcupine_model_path: Optional[Path] = None
    porcupine_keyword_paths: Optional[List[Path]] = None
    porcupine_sensitivity: float = 0.7
    # Keyword settings for VAD-based
    keyword: str = "hey cell"
    keyword_threshold: float = 0.6
    # Audio settings
    sample_rate: int = 16000
    frame_length: int = 512  # 32ms at 16kHz
    # Detection settings
    buffer_duration_ms: int = 3000  # Keep last 3 seconds
    cooldown_ms: int = 2000  # Minimum time between detections


@dataclass
class WakeWordEvent:
    """Wake word detection event"""
    keyword: str
    confidence: float
    timestamp: float
    audio_buffer: Optional[bytes] = None  # Audio context around detection


class BaseWakeWord(ABC):
    """Abstract base class for wake word detectors"""
    
    @abstractmethod
    async def process_chunk(self, audio_chunk: bytes) -> Optional[WakeWordEvent]:
        """Process audio chunk and return event if wake word detected"""
        pass
    
    @abstractmethod
    async def listen_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[WakeWordEvent]:
        """Listen to audio stream and yield wake word events"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    @abstractmethod
    async def close(self):
        """Clean up resources"""
        pass


class PorcupineWakeWord(BaseWakeWord):
    """Picovoice Porcupine wake word detection"""
    
    def __init__(self, config: WakeWordConfig, access_key: Optional[str] = None):
        self.config = config
        self.access_key = access_key or self._get_access_key()
        self.porcupine = None
        self._last_detection_time = 0
        self._cooldown_seconds = config.cooldown_ms / 1000.0
        
    def _get_access_key(self) -> str:
        """Get Picovoice access key from 1Password or environment"""
        access_key = os.environ.get("PICOVOICE_ACCESS_KEY")
        if access_key:
            return access_key
        
        # Try 1Password
        try:
            result = subprocess.run(
                ["op", "read", "op://Private/Picovoice/credential"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        raise ValueError("Picovoice access key not found")
    
    def _initialize(self):
        """Initialize Porcupine engine"""
        try:
            from pvporcupine import Porcupine, create
            
            # Find keyword files
            keyword_paths = self.config.porcupine_keyword_paths
            if not keyword_paths:
                # Use built-in keywords
                keyword_paths = ["hey google", "alexa", "computer"]
            
            if isinstance(keyword_paths[0], str):
                # Built-in keywords
                self.porcupine = create(
                    access_key=self.access_key,
                    keywords=keyword_paths,
                    sensitivities=[self.config.porcupine_sensitivity] * len(keyword_paths)
                )
            else:
                # Custom keyword files
                self.porcupine = Porcupine(
                    access_key=self.access_key,
                    keyword_paths=[str(p) for p in keyword_paths],
                    sensitivities=[self.config.porcupine_sensitivity] * len(keyword_paths)
                )
            
            logger.info(f"Porcupine initialized with {len(keyword_paths)} keywords")
            
        except ImportError:
            raise RuntimeError("pvporcupine not installed. Run: pip install pvporcupine")
    
    def is_available(self) -> bool:
        """Check if Porcupine is available"""
        try:
            import pvporcupine
            return True
        except ImportError:
            return False
    
    async def process_chunk(self, audio_chunk: bytes) -> Optional[WakeWordEvent]:
        """Process audio chunk for wake word"""
        if self.porcupine is None:
            self._initialize()
        
        # Convert bytes to PCM16
        pcm_data = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # Ensure correct frame length
        frame_length = self.porcupine.frame_length
        if len(pcm_data) != frame_length:
            logger.warning(f"Expected {frame_length} samples, got {len(pcm_data)}")
            return None
        
        # Process
        result = self.porcupine.process(pcm_data)
        
        if result >= 0:
            current_time = asyncio.get_event_loop().time()
            
            # Check cooldown
            if current_time - self._last_detection_time < self._cooldown_seconds:
                return None
            
            self._last_detection_time = current_time
            
            return WakeWordEvent(
                keyword=f"keyword_{result}",
                confidence=1.0,
                timestamp=current_time
            )
        
        return None
    
    async def listen_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[WakeWordEvent]:
        """Listen to audio stream"""
        if self.porcupine is None:
            self._initialize()
        
        frame_length = self.porcupine.frame_length * 2  # 2 bytes per int16
        buffer = bytearray()
        
        async for chunk in audio_stream:
            buffer.extend(chunk)
            
            # Process complete frames
            while len(buffer) >= frame_length:
                frame = bytes(buffer[:frame_length])
                buffer = buffer[frame_length:]
                
                event = await self.process_chunk(frame)
                if event:
                    yield event
    
    async def close(self):
        """Clean up Porcupine resources"""
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None


class VADKeywordWakeWord(BaseWakeWord):
    """VAD-based wake word detection with keyword matching"""
    
    def __init__(self, config: WakeWordConfig):
        self.config = config
        self.vad = None
        self._audio_buffer = bytearray()
        self._buffer_samples = int(config.sample_rate * (config.buffer_duration_ms / 1000.0))
        self._last_detection_time = 0
        self._cooldown_seconds = config.cooldown_ms / 1000.0
        self._is_speech_active = False
        self._speech_start_time = 0
        
    def _initialize(self):
        """Initialize VAD"""
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(2)  # Aggressiveness 0-3
            logger.info("WebRTC VAD initialized")
        except ImportError:
            logger.warning("webrtcvad not installed, using simple energy detection")
            self.vad = None
    
    def is_available(self) -> bool:
        """Always available (has fallback)"""
        return True
    
    def _is_speech(self, audio_chunk: bytes) -> bool:
        """Check if audio chunk contains speech"""
        if self.vad:
            try:
                import webrtcvad
                return self.vad.is_speech(audio_chunk, self.config.sample_rate)
            except:
                pass
        
        # Fallback: simple energy detection
        pcm = np.frombuffer(audio_chunk, dtype=np.int16)
        energy = np.sqrt(np.mean(pcm.astype(np.float32) ** 2))
        return energy > 500  # Threshold
    
    def _extract_keyword_audio(self) -> bytes:
        """Extract keyword portion from buffer"""
        return bytes(self._audio_buffer)
    
    def _match_keyword(self, text: str) -> tuple[bool, float]:
        """Simple keyword matching (would use STT in real implementation)"""
        keyword = self.config.keyword.lower()
        text_lower = text.lower()
        
        # Simple string matching (placeholder for actual STT-based matching)
        if keyword in text_lower:
            return True, 1.0
        
        # Check for similar sounds (very basic)
        keyword_words = keyword.split()
        text_words = text_lower.split()
        
        matches = sum(1 for kw in keyword_words if any(kw in tw for tw in text_words))
        if matches > 0:
            confidence = matches / len(keyword_words)
            return confidence >= self.config.keyword_threshold, confidence
        
        return False, 0.0
    
    async def process_chunk(self, audio_chunk: bytes) -> Optional[WakeWordEvent]:
        """Process audio chunk"""
        if self.vad is None:
            self._initialize()
        
        # Add to buffer (circular)
        self._audio_buffer.extend(audio_chunk)
        max_buffer_bytes = self._buffer_samples * 2  # 16-bit
        if len(self._audio_buffer) > max_buffer_bytes:
            self._audio_buffer = self._audio_buffer[-max_buffer_bytes:]
        
        # Check for speech
        is_speech = self._is_speech(audio_chunk)
        
        if is_speech and not self._is_speech_active:
            # Speech started
            self._is_speech_active = True
            self._speech_start_time = asyncio.get_event_loop().time()
        elif not is_speech and self._is_speech_active:
            # Speech ended - check for keyword
            self._is_speech_active = False
            
            current_time = asyncio.get_event_loop().time()
            
            # Check cooldown
            if current_time - self._last_detection_time < self._cooldown_seconds:
                return None
            
            # Get speech duration
            speech_duration = current_time - self._speech_start_time
            
            # Minimum speech duration for keyword
            if speech_duration < 0.5:  # 500ms
                return None
            
            # This is a placeholder - in real implementation would:
            # 1. Extract the speech portion from buffer
            # 2. Run STT on it
            # 3. Match against keyword
            
            # For now, simulate detection
            self._last_detection_time = current_time
            
            return WakeWordEvent(
                keyword=self.config.keyword,
                confidence=0.8,
                timestamp=current_time,
                audio_buffer=bytes(self._audio_buffer)
            )
        
        return None
    
    async def listen_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[WakeWordEvent]:
        """Listen to audio stream"""
        async for chunk in audio_stream:
            event = await self.process_chunk(chunk)
            if event:
                yield event
    
    async def close(self):
        """Clean up"""
        self.vad = None


class OpenWakeWord(BaseWakeWord):
    """OpenWakeWord open-source wake word detection"""
    
    def __init__(self, config: WakeWordConfig):
        self.config = config
        self.oww = None
        
    def _initialize(self):
        """Initialize OpenWakeWord"""
        try:
            from openwakeword.model import Model
            
            # Find or download models
            model_paths = []
            
            # Common wake word models
            common_models = [
                "hey_jarvis",
                "alexa", 
                "hey_mycroft"
            ]
            
            self.oww = Model(
                wakeword_models=model_paths if model_paths else None,
                enable_speex_noise_suppression=True,
                inference_framework="onnx"
            )
            
            logger.info("OpenWakeWord initialized")
            
        except ImportError:
            raise RuntimeError("openwakeword not installed. Run: pip install openwakeword")
    
    def is_available(self) -> bool:
        """Check if OpenWakeWord is available"""
        try:
            import openwakeword
            return True
        except ImportError:
            return False
    
    async def process_chunk(self, audio_chunk: bytes) -> Optional[WakeWordEvent]:
        """Process audio chunk"""
        if self.oww is None:
            self._initialize()
        
        # Convert to numpy array
        pcm = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # Get prediction
        prediction = self.oww.predict(pcm)
        
        if prediction:
            # Check for any model above threshold
            for model_name, score in prediction.items():
                if score > self.config.keyword_threshold:
                    return WakeWordEvent(
                        keyword=model_name,
                        confidence=score,
                        timestamp=asyncio.get_event_loop().time()
                    )
        
        return None
    
    async def listen_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[WakeWordEvent]:
        """Listen to audio stream"""
        async for chunk in audio_stream:
            event = await self.process_chunk(chunk)
            if event:
                yield event
    
    async def close(self):
        """Clean up"""
        if self.oww:
            del self.oww
            self.oww = None


class WakeWordManager:
    """Manager for wake word detection with automatic fallback"""
    
    def __init__(self, config: Optional[WakeWordConfig] = None):
        self.config = config or WakeWordConfig()
        self.providers: dict[WakeWordProvider, BaseWakeWord] = {}
        self._current_provider: Optional[BaseWakeWord] = None
        
    def _initialize_providers(self):
        """Initialize all available wake word providers"""
        # Try Porcupine first
        try:
            porcupine = PorcupineWakeWord(self.config)
            if porcupine.is_available():
                self.providers[WakeWordProvider.PORCUPINE] = porcupine
                logger.info("Porcupine wake word initialized")
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Porcupine not available: {e}")
        
        # Try OpenWakeWord
        try:
            oww = OpenWakeWord(self.config)
            if oww.is_available():
                self.providers[WakeWordProvider.OPENWAKEWORD] = oww
                logger.info("OpenWakeWord initialized")
        except (ValueError, RuntimeError) as e:
            logger.warning(f"OpenWakeWord not available: {e}")
        
        # VAD + Keyword (always available as fallback)
        vad_keyword = VADKeywordWakeWord(self.config)
        self.providers[WakeWordProvider.VAD_KEYWORD] = vad_keyword
        logger.info("VAD+Keyword wake word initialized")
        
        # Select primary provider
        preferred_order = [
            WakeWordProvider.PORCUPINE,
            WakeWordProvider.OPENWAKEWORD,
            WakeWordProvider.VAD_KEYWORD
        ]
        
        for provider in preferred_order:
            if provider in self.providers:
                self._current_provider = self.providers[provider]
                logger.info(f"Using wake word provider: {provider.value}")
                break
    
    @property
    def current_provider(self) -> BaseWakeWord:
        """Get current wake word provider"""
        if self._current_provider is None:
            self._initialize_providers()
        return self._current_provider
    
    async def listen(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[WakeWordEvent]:
        """Listen for wake word in audio stream"""
        async for event in self.current_provider.listen_stream(audio_stream):
            yield event
    
    async def process_chunk(self, audio_chunk: bytes) -> Optional[WakeWordEvent]:
        """Process single audio chunk"""
        return await self.current_provider.process_chunk(audio_chunk)
    
    def switch_provider(self, provider: WakeWordProvider) -> bool:
        """Switch to specific provider"""
        if provider in self.providers:
            self._current_provider = self.providers[provider]
            logger.info(f"Switched to wake word provider: {provider.value}")
            return True
        return False
    
    def list_available_providers(self) -> list[WakeWordProvider]:
        """List available providers"""
        if not self.providers:
            self._initialize_providers()
        return list(self.providers.keys())
    
    async def close(self):
        """Close all providers"""
        for provider in self.providers.values():
            await provider.close()
