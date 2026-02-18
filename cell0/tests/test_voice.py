"""
Tests for Cell 0 OS Voice Integration
"""

import asyncio
import io
import json
import os
import platform
import tempfile
import wave
from pathlib import Path
from unittest import mock

import pytest
import numpy as np

# Import modules to test
from cell0.engine.voice.tts import (
    TTSManager, TTSConfig, TTSProvider,
    MacOSSayTTS, LinuxEspeakTTS
)
from cell0.engine.voice.stt import (
    STTManager, STTConfig, STTProvider, TranscriptionResult
)
from cell0.engine.voice.wake_word import (
    WakeWordManager, WakeWordConfig, WakeWordProvider,
    VADKeywordWakeWord, WakeWordEvent
)
from cell0.engine.voice.voice_session import (
    VoiceSession, VoiceSessionConfig, SessionState, VoiceInteraction
)
from cell0.engine.voice.audio_player import AudioPlayer, MacOSAudioPlayer, LinuxAudioPlayer


# ============== Fixtures ==============

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_audio_data():
    """Generate sample 16kHz 16-bit mono audio data"""
    duration = 1.0  # 1 second
    sample_rate = 16000
    frequency = 440  # A4 note
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t) * 32767
    audio = audio.astype(np.int16)
    
    return audio.tobytes()


@pytest.fixture
def sample_wav_file(sample_audio_data):
    """Create a temporary WAV file"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        with wave.open(f, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(sample_audio_data)
        return Path(f.name)


# ============== TTS Tests ==============

class TestTTSConfig:
    """Test TTS configuration"""
    
    def test_default_config(self):
        config = TTSConfig()
        assert config.provider == TTSProvider.ELEVENLABS
        assert config.voice_id == "21m00Tcm4TlvDq8ikWAM"
        assert config.enable_streaming is True
    
    def test_custom_config(self):
        config = TTSConfig(
            provider=TTSProvider.MACOS_SAY,
            voice="Alex",
            rate=200
        )
        assert config.provider == TTSProvider.MACOS_SAY
        assert config.voice == "Alex"
        assert config.rate == 200


class TestMacOSTTS:
    """Test macOS TTS (if on macOS)"""
    
    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_is_available(self):
        tts = MacOSSayTTS(TTSConfig())
        assert tts.is_available() is True
    
    @pytest.mark.skipif(platform.system() == "Darwin", reason="Not on macOS")
    def test_not_available(self):
        tts = MacOSSayTTS(TTSConfig())
        assert tts.is_available() is False
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    async def test_synthesize(self):
        tts = MacOSSayTTS(TTSConfig())
        output_path = await tts.synthesize("Hello test")
        assert output_path.exists()
        assert output_path.suffix == ".aiff"
        output_path.unlink(missing_ok=True)


class TestLinuxTTS:
    """Test Linux TTS"""
    
    def test_is_available_on_linux(self):
        # Mock the availability check
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            tts = LinuxEspeakTTS(TTSConfig())
            
            # Force platform to Linux
            with mock.patch('platform.system', return_value='Linux'):
                assert tts.is_available() is True


class TestTTSManager:
    """Test TTS Manager"""
    
    def test_initialization(self):
        manager = TTSManager()
        # Should initialize with available providers
        providers = manager.list_available_providers()
        assert isinstance(providers, list)
    
    @pytest.mark.asyncio
    async def test_provider_switching(self):
        manager = TTSManager()
        
        # Get available providers
        providers = manager.list_available_providers()
        if len(providers) > 1:
            # Try switching to each provider
            for provider in providers:
                result = manager.switch_provider(provider)
                assert result is True
                assert manager.current_provider is not None


# ============== STT Tests ==============

class TestSTTConfig:
    """Test STT configuration"""
    
    def test_default_config(self):
        config = STTConfig()
        assert config.provider == STTProvider.WHISPER_API
        assert config.model_size == "base"
        assert config.enable_streaming is True
    
    def test_custom_config(self):
        config = STTConfig(
            provider=STTProvider.WHISPER_CPP,
            model_size="small",
            language="en"
        )
        assert config.provider == STTProvider.WHISPER_CPP
        assert config.model_size == "small"
        assert config.language == "en"


class TestSTTManager:
    """Test STT Manager"""
    
    def test_initialization(self):
        manager = STTManager()
        providers = manager.list_available_providers()
        assert isinstance(providers, list)
    
    @pytest.mark.asyncio
    async def test_transcription_result(self):
        result = TranscriptionResult(
            text="Hello world",
            language="en",
            confidence=0.95
        )
        assert result.text == "Hello world"
        assert result.confidence == 0.95


# ============== Wake Word Tests ==============

class TestWakeWordConfig:
    """Test wake word configuration"""
    
    def test_default_config(self):
        config = WakeWordConfig()
        assert config.provider == WakeWordProvider.VAD_KEYWORD
        assert config.keyword == "hey cell"
        assert config.sample_rate == 16000
    
    def test_custom_config(self):
        config = WakeWordConfig(
            keyword="hello assistant",
            vad_threshold=0.7,
            cooldown_ms=3000
        )
        assert config.keyword == "hello assistant"
        assert config.vad_threshold == 0.7
        assert config.cooldown_ms == 3000


class TestVADWakeWord:
    """Test VAD-based wake word detection"""
    
    def test_is_available(self):
        detector = VADKeywordWakeWord(WakeWordConfig())
        assert detector.is_available() is True  # Always available
    
    @pytest.mark.asyncio
    async def test_speech_detection(self, sample_audio_data):
        detector = VADKeywordWakeWord(WakeWordConfig())
        
        # Process chunks
        chunk_size = 512 * 2  # 512 samples * 2 bytes
        for i in range(0, len(sample_audio_data), chunk_size):
            chunk = sample_audio_data[i:i+chunk_size]
            if len(chunk) == chunk_size:
                await detector.process_chunk(chunk)


class TestWakeWordManager:
    """Test Wake Word Manager"""
    
    def test_initialization(self):
        manager = WakeWordManager()
        providers = manager.list_available_providers()
        # Should have at least VAD_KEYWORD
        assert WakeWordProvider.VAD_KEYWORD in providers


# ============== Voice Session Tests ==============

class TestVoiceSessionConfig:
    """Test voice session configuration"""
    
    def test_default_config(self):
        config = VoiceSessionConfig()
        assert config.auto_start is True
        assert config.continuous_mode is True
        assert config.command_timeout_ms == 10000
    
    def test_callbacks(self):
        callbacks = []
        
        def on_wake(event):
            callbacks.append("wake")
        
        def on_command(result):
            callbacks.append("command")
        
        config = VoiceSessionConfig(
            on_wake_word=on_wake,
            on_command=on_command
        )
        
        # Simulate callbacks
        config.on_wake_word(None)
        config.on_command(None)
        
        assert "wake" in callbacks
        assert "command" in callbacks


class TestVoiceSession:
    """Test voice session"""
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        session = VoiceSession()
        
        # Start
        await session.start()
        assert session._running is True
        
        # Stop
        await session.stop()
        assert session._running is False
    
    @pytest.mark.asyncio
    async def test_state_transitions(self):
        config = VoiceSessionConfig()
        session = VoiceSession(config)
        
        states = []
        config.on_state_change = lambda old, new: states.append((old, new))
        
        await session.start()
        await session.stop()
        
        assert len(states) > 0


class TestVoiceInteraction:
    """Test voice interaction record"""
    
    def test_interaction_creation(self):
        from datetime import datetime
        
        interaction = VoiceInteraction(
            timestamp=datetime.now(),
            wake_word="hey cell",
            command_text="what time is it",
            response_text="The time is 3:00 PM",
            duration_ms=1500.0,
            confidence=0.92
        )
        
        assert interaction.wake_word == "hey cell"
        assert interaction.command_text == "what time is it"
        assert interaction.confidence == 0.92


# ============== Audio Player Tests ==============

class TestAudioPlayer:
    """Test audio player"""
    
    def test_initialization(self):
        # Should select appropriate player for platform
        try:
            player = AudioPlayer()
            assert player._player is not None
        except RuntimeError:
            # No player available (expected in test environment)
            pass
    
    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_macos_player(self):
        player = MacOSAudioPlayer()
        assert player.is_available() is True


# ============== Integration Tests ==============

class TestVoiceIntegration:
    """Integration tests for voice system"""
    
    @pytest.mark.asyncio
    async def test_full_session(self, sample_wav_file):
        """Test a complete voice session flow"""
        config = VoiceSessionConfig(
            auto_start=True,
            continuous_mode=False
        )
        
        session = VoiceSession(config)
        
        # Start session
        await session.start()
        assert session.state == SessionState.LISTENING_WAKE
        
        # Simulate receiving audio
        async def audio_stream():
            with open(sample_wav_file, 'rb') as f:
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    yield chunk
        
        # Process audio
        await session.process_audio_stream(audio_stream())
        
        # Clean up
        await session.stop()
    
    @pytest.mark.asyncio
    async def test_tts_stt_integration(self):
        """Test TTS and STT integration"""
        # Create TTS and STT managers
        tts = TTSManager()
        stt = STTManager()
        
        # Verify providers are available
        tts_providers = tts.list_available_providers()
        stt_providers = stt.list_available_providers()
        
        assert isinstance(tts_providers, list)
        assert isinstance(stt_providers, list)
        
        # Clean up
        await tts.close()
        await stt.close()


# ============== Performance Tests ==============

class TestPerformance:
    """Performance benchmarks"""
    
    @pytest.mark.asyncio
    async def test_audio_processing_speed(self, sample_audio_data):
        """Test audio processing performance"""
        detector = VADKeywordWakeWord(WakeWordConfig())
        
        chunk_size = 512 * 2
        chunks = [sample_audio_data[i:i+chunk_size] 
                  for i in range(0, len(sample_audio_data), chunk_size)
                  if len(sample_audio_data[i:i+chunk_size]) == chunk_size]
        
        start = asyncio.get_event_loop().time()
        
        for chunk in chunks:
            await detector.process_chunk(chunk)
        
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should process 1 second of audio in less than 0.5 seconds
        assert elapsed < 0.5


# ============== Error Handling Tests ==============

class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_audio_data(self):
        """Test handling of invalid audio data"""
        detector = VADKeywordWakeWord(WakeWordConfig())
        
        # Process invalid data (should not crash)
        result = await detector.process_chunk(b"invalid data")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_session_error_callback(self):
        """Test error callback"""
        errors = []
        
        config = VoiceSessionConfig(
            on_error=lambda e: errors.append(str(e))
        )
        
        session = VoiceSession(config)
        
        # Simulate error
        if config.on_error:
            config.on_error(Exception("Test error"))
        
        assert len(errors) == 1
        assert "Test error" in errors[0]


# ============== Run Tests ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
