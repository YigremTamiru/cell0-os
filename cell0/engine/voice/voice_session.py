"""
Voice Session Manager for Cell 0 OS
Manages voice interaction sessions with wake word, STT, and TTS
"""

import asyncio
import io
import json
import logging
import tempfile
import wave
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Callable, AsyncIterator, Any
import numpy as np

from .tts import TTSManager, TTSConfig
from .stt import STTManager, STTConfig, TranscriptionResult
from .wake_word import WakeWordManager, WakeWordConfig, WakeWordEvent
from .audio_player import AudioPlayer

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Voice session states"""
    IDLE = auto()
    LISTENING_WAKE = auto()  # Listening for wake word
    LISTENING_COMMAND = auto()  # Listening for command after wake
    PROCESSING = auto()  # Processing speech
    SPEAKING = auto()  # Speaking response
    PAUSED = auto()  # Session paused


@dataclass
class VoiceSessionConfig:
    """Configuration for voice session"""
    # TTS configuration
    tts_config: TTSConfig = field(default_factory=TTSConfig)
    # STT configuration
    stt_config: STTConfig = field(default_factory=STTConfig)
    # Wake word configuration
    wake_word_config: WakeWordConfig = field(default_factory=WakeWordConfig)
    # Session settings
    auto_start: bool = True
    continuous_mode: bool = True  # Keep listening after response
    command_timeout_ms: int = 10000  # Max time to wait for command
    min_speech_duration_ms: int = 500
    max_speech_duration_ms: int = 30000
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 20  # 20ms chunks
    # Callbacks
    on_wake_word: Optional[Callable[[WakeWordEvent], None]] = None
    on_command: Optional[Callable[[TranscriptionResult], None]] = None
    on_response: Optional[Callable[[str], None]] = None
    on_state_change: Optional[Callable[[SessionState, SessionState], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None


@dataclass
class VoiceInteraction:
    """Record of a voice interaction"""
    timestamp: datetime
    wake_word: Optional[str]
    command_text: str
    response_text: str
    duration_ms: float
    confidence: float


class VoiceActivityDetector:
    """Simple voice activity detector"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        silence_duration_ms: int = 1000,
        min_speech_duration_ms: int = 500
    ):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.silence_duration_ms = silence_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        
        self._is_speaking = False
        self._speech_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._buffer = bytearray()
        
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(2)
        except ImportError:
            self.vad = None
    
    def process_chunk(self, audio_chunk: bytes) -> tuple[bool, Optional[bytes]]:
        """
        Process audio chunk and detect voice activity
        Returns: (is_speech, complete_utterance)
        """
        current_time = asyncio.get_event_loop().time()
        
        # Determine if speech
        is_speech = self._detect_speech(audio_chunk)
        
        if is_speech:
            self._last_speech_time = current_time
            
            if not self._is_speaking:
                # Speech started
                self._is_speaking = True
                self._speech_start_time = current_time
                self._buffer = bytearray(audio_chunk)
            else:
                # Continuing speech
                self._buffer.extend(audio_chunk)
        else:
            if self._is_speaking:
                # Check if silence duration exceeded
                silence_duration = (current_time - self._last_speech_time) * 1000
                
                if silence_duration > self.silence_duration_ms:
                    # Speech ended
                    speech_duration = (self._last_speech_time - self._speech_start_time) * 1000
                    
                    if speech_duration >= self.min_speech_duration_ms:
                        # Valid utterance
                        utterance = bytes(self._buffer)
                        self._reset()
                        return False, utterance
                    else:
                        # Too short, discard
                        self._reset()
        
        return is_speech, None
    
    def _detect_speech(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains speech"""
        if self.vad:
            try:
                return self.vad.is_speech(audio_chunk, self.sample_rate)
            except:
                pass
        
        # Fallback: energy-based detection
        pcm = np.frombuffer(audio_chunk, dtype=np.int16)
        energy = np.sqrt(np.mean(pcm.astype(np.float32) ** 2))
        normalized_energy = min(energy / 32768.0, 1.0)
        return normalized_energy > self.threshold
    
    def _reset(self):
        """Reset detector state"""
        self._is_speaking = False
        self._speech_start_time = None
        self._last_speech_time = None
        self._buffer = bytearray()
    
    def reset(self):
        """Public reset"""
        self._reset()


class VoiceSession:
    """Manages a voice interaction session"""
    
    def __init__(self, config: Optional[VoiceSessionConfig] = None):
        self.config = config or VoiceSessionConfig()
        self.state = SessionState.IDLE
        
        # Managers
        self.tts = TTSManager(self.config.tts_config)
        self.stt = STTManager(self.config.stt_config)
        self.wake_word = WakeWordManager(self.config.wake_word_config)
        self.audio_player = AudioPlayer()
        
        # VAD for command detection
        self.vad = VoiceActivityDetector(
            sample_rate=self.config.sample_rate,
            silence_duration_ms=self.config.stt_config.silence_duration_ms if self.config.stt_config.enable_vad else 1000
        )
        
        # State
        self._running = False
        self._current_task: Optional[asyncio.Task] = None
        self._interaction_history: list[VoiceInteraction] = []
        self._command_timeout_task: Optional[asyncio.Task] = None
        
    def _set_state(self, new_state: SessionState):
        """Change session state with callback"""
        old_state = self.state
        self.state = new_state
        
        if self.config.on_state_change:
            try:
                self.config.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")
        
        logger.info(f"Session state: {old_state.name} -> {new_state.name}")
    
    async def start(self):
        """Start the voice session"""
        if self._running:
            return
        
        self._running = True
        self._set_state(SessionState.LISTENING_WAKE)
        
        logger.info("Voice session started")
    
    async def stop(self):
        """Stop the voice session"""
        self._running = False
        
        if self._current_task:
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError:
                pass
        
        if self._command_timeout_task:
            self._command_timeout_task.cancel()
        
        await self.tts.close()
        await self.stt.close()
        await self.wake_word.close()
        
        self._set_state(SessionState.IDLE)
        logger.info("Voice session stopped")
    
    async def pause(self):
        """Pause the session"""
        self._set_state(SessionState.PAUSED)
    
    async def resume(self):
        """Resume the session"""
        if self._running:
            self._set_state(SessionState.LISTENING_WAKE)
    
    async def process_audio_stream(self, audio_stream: AsyncIterator[bytes]):
        """Process incoming audio stream"""
        if not self._running:
            await self.start()
        
        try:
            if self.state == SessionState.LISTENING_WAKE:
                await self._listen_for_wake_word(audio_stream)
            elif self.state == SessionState.LISTENING_COMMAND:
                await self._listen_for_command(audio_stream)
            else:
                # Consume stream but ignore
                async for _ in audio_stream:
                    pass
                    
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            if self.config.on_error:
                self.config.on_error(e)
    
    async def _listen_for_wake_word(self, audio_stream: AsyncIterator[bytes]):
        """Listen for wake word"""
        logger.info("Listening for wake word...")
        
        async for event in self.wake_word.listen(audio_stream):
            logger.info(f"Wake word detected: {event.keyword}")
            
            if self.config.on_wake_word:
                try:
                    self.config.on_wake_word(event)
                except Exception as e:
                    logger.error(f"Wake word callback error: {e}")
            
            # Transition to command listening
            self._set_state(SessionState.LISTENING_COMMAND)
            
            # Start command timeout
            self._start_command_timeout()
            
            # If continuous, break to let caller restart with new stream
            if not self.config.continuous_mode:
                break
    
    async def _listen_for_command(self, audio_stream: AsyncIterator[bytes]):
        """Listen for voice command after wake word"""
        logger.info("Listening for command...")
        
        command_buffer = bytearray()
        start_time = asyncio.get_event_loop().time()
        max_duration = self.config.max_speech_duration_ms / 1000.0
        
        async for chunk in audio_stream:
            # Check max duration
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_duration:
                logger.warning("Command timeout (max duration)")
                break
            
            # Process with VAD
            is_speech, utterance = self.vad.process_chunk(chunk)
            
            if utterance:
                # Got complete utterance
                await self._process_command(utterance)
                return
            elif is_speech:
                command_buffer.extend(chunk)
        
        # Process any remaining audio
        if len(command_buffer) > 0:
            await self._process_command(bytes(command_buffer))
    
    async def _process_command(self, audio_data: bytes):
        """Process command audio"""
        self._set_state(SessionState.PROCESSING)
        
        # Cancel timeout
        if self._command_timeout_task:
            self._command_timeout_task.cancel()
            self._command_timeout_task = None
        
        try:
            # Transcribe
            result = await self.stt.transcribe_buffer(audio_data)
            
            logger.info(f"Command transcribed: {result.text}")
            
            if self.config.on_command:
                try:
                    self.config.on_command(result)
                except Exception as e:
                    logger.error(f"Command callback error: {e}")
            
            # Store interaction
            interaction = VoiceInteraction(
                timestamp=datetime.now(),
                wake_word=self.config.wake_word_config.keyword,
                command_text=result.text,
                response_text="",  # To be filled after response
                duration_ms=0,
                confidence=result.confidence or 0.0
            )
            self._interaction_history.append(interaction)
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            if self.config.on_error:
                self.config.on_error(e)
        
        finally:
            # Return to wake word listening
            if self.config.continuous_mode:
                self.vad.reset()
                self._set_state(SessionState.LISTENING_WAKE)
            else:
                self._set_state(SessionState.IDLE)
    
    async def speak(self, text: str) -> None:
        """Speak response text"""
        self._set_state(SessionState.SPEAKING)
        
        try:
            await self.tts.play(text)
            
            if self.config.on_response:
                try:
                    self.config.on_response(text)
                except Exception as e:
                    logger.error(f"Response callback error: {e}")
            
            # Update last interaction
            if self._interaction_history:
                self._interaction_history[-1].response_text = text
        
        finally:
            if self.config.continuous_mode and self._running:
                self._set_state(SessionState.LISTENING_WAKE)
            else:
                self._set_state(SessionState.IDLE)
    
    def _start_command_timeout(self):
        """Start timeout for command input"""
        async def timeout_handler():
            await asyncio.sleep(self.config.command_timeout_ms / 1000.0)
            logger.info("Command timeout")
            self.vad.reset()
            self._set_state(SessionState.LISTENING_WAKE)
        
        self._command_timeout_task = asyncio.create_task(timeout_handler())
    
    def get_history(self) -> list[VoiceInteraction]:
        """Get interaction history"""
        return self._interaction_history.copy()
    
    def clear_history(self):
        """Clear interaction history"""
        self._interaction_history.clear()


class VoiceSessionManager:
    """Manages multiple voice sessions"""
    
    def __init__(self):
        self.sessions: dict[str, VoiceSession] = {}
        self._default_config = VoiceSessionConfig()
    
    def create_session(
        self,
        session_id: str,
        config: Optional[VoiceSessionConfig] = None
    ) -> VoiceSession:
        """Create a new voice session"""
        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} already exists")
        
        session = VoiceSession(config or self._default_config)
        self.sessions[session_id] = session
        
        logger.info(f"Created voice session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get existing session"""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str):
        """Close and remove a session"""
        if session_id in self.sessions:
            await self.sessions[session_id].stop()
            del self.sessions[session_id]
            logger.info(f"Closed voice session: {session_id}")
    
    async def close_all(self):
        """Close all sessions"""
        for session in list(self.sessions.values()):
            await session.stop()
        self.sessions.clear()
        logger.info("All voice sessions closed")
