"""
Cell 0 OS Voice Integration Module
Provides TTS, STT, wake word detection, and voice session management
"""

from .tts import (
    TTSManager,
    TTSConfig,
    TTSProvider,
    ElevenLabsTTS,
    MacOSSayTTS,
    LinuxEspeakTTS,
    speak
)

from .stt import (
    STTManager,
    STTConfig,
    STTProvider,
    WhisperAPISTT,
    WhisperCppSTT,
    WhisperLocalSTT,
    TranscriptionResult
)

from .wake_word import (
    WakeWordManager,
    WakeWordConfig,
    WakeWordProvider,
    WakeWordEvent,
    PorcupineWakeWord,
    VADKeywordWakeWord,
    OpenWakeWord
)

from .voice_session import (
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionManager,
    SessionState,
    VoiceInteraction
)

from .audio_player import AudioPlayer

__all__ = [
    # TTS
    "TTSManager",
    "TTSConfig", 
    "TTSProvider",
    "ElevenLabsTTS",
    "MacOSSayTTS",
    "LinuxEspeakTTS",
    "speak",
    # STT
    "STTManager",
    "STTConfig",
    "STTProvider",
    "WhisperAPISTT",
    "WhisperCppSTT",
    "WhisperLocalSTT",
    "TranscriptionResult",
    # Wake Word
    "WakeWordManager",
    "WakeWordConfig",
    "WakeWordProvider",
    "WakeWordEvent",
    "PorcupineWakeWord",
    "VADKeywordWakeWord",
    "OpenWakeWord",
    # Session
    "VoiceSession",
    "VoiceSessionConfig",
    "VoiceSessionManager",
    "SessionState",
    "VoiceInteraction",
    # Audio
    "AudioPlayer"
]

__version__ = "0.1.0"
