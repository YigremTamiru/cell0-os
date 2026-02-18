# Cell 0 OS Voice Integration

Real-time voice integration system for Cell 0 OS with TTS, STT, wake word detection, and voice session management.

## Architecture

```
cell0/engine/voice/
├── __init__.py           # Module exports
├── tts.py                # Text-to-Speech (ElevenLabs, macOS say, Linux espeak)
├── stt.py                # Speech-to-Text (Whisper API, whisper.cpp, local)
├── wake_word.py          # Wake word detection (Porcupine, OpenWakeWord, VAD)
├── voice_session.py      # Voice session manager
└── audio_player.py       # Cross-platform audio playback

cell0/service/
└── voice_gateway.py      # WebSocket gateway (port 18803)

cell0/tests/
└── test_voice.py         # Test suite
```

## Features

### TTS (Text-to-Speech)
- **Primary**: ElevenLabs API with streaming support
- **macOS Fallback**: `say` command
- **Linux Fallback**: `espeak` command
- API keys via 1Password integration

### STT (Speech-to-Text)
- **Primary**: OpenAI Whisper API
- **Local Option**: whisper.cpp (fast, offline)
- **Python Option**: OpenAI whisper package
- Automatic audio format conversion

### Wake Word Detection
- **Primary**: Picovoice Porcupine (accurate, commercial)
- **Open Source**: OpenWakeWord
- **Fallback**: VAD + keyword matching (always works)

### Voice Session Management
- Complete voice interaction lifecycle
- State machine: IDLE → LISTENING_WAKE → LISTENING_COMMAND → PROCESSING → SPEAKING
- Automatic fallback chain for all components
- Continuous or single-shot listening modes

### Voice Gateway (WebSocket)
- Port: 18803
- Binary audio streaming
- JSON control messages
- Multi-client support

## Installation

### Dependencies

```bash
# Core dependencies
pip install aiohttp aiofiles websockets numpy

# Optional: PyAudio for low-latency playback
pip install pyaudio

# Optional: WebRTC VAD for better voice detection
pip install webrtcvad

# Optional: Porcupine wake word
pip install pvporcupine

# Optional: OpenWakeWord (open source)
pip install openwakeword

# Optional: Local whisper
pip install openai-whisper

# Optional: whisper.cpp Python bindings
pip install pywhispercpp
```

### 1Password Integration

API keys are retrieved from 1Password CLI:

```bash
# Store keys in 1Password
op item create \
  --category=password \
  --title="ElevenLabs" \
  credential="your-api-key"

op item create \
  --category=password \
  --title="OpenAI" \
  credential="your-api-key"

op item create \
  --category=password \
  --title="Picovoice" \
  credential="your-access-key"
```

## Usage

### Basic TTS

```python
import asyncio
from cell0.engine.voice import speak

async def main():
    await speak("Hello, this is Cell 0 speaking")

asyncio.run(main())
```

### Basic STT

```python
import asyncio
from cell0.engine.voice import STTManager

async def main():
    stt = STTManager()
    result = await stt.transcribe(Path("audio.wav"))
    print(f"Transcribed: {result.text}")
    await stt.close()

asyncio.run(main())
```

### Voice Session

```python
import asyncio
from cell0.engine.voice import VoiceSession, VoiceSessionConfig

async def main():
    config = VoiceSessionConfig(
        on_wake_word=lambda e: print(f"Wake word: {e.keyword}"),
        on_command=lambda r: print(f"Command: {r.text}"),
        on_response=lambda t: print(f"Response: {t}")
    )
    
    session = VoiceSession(config)
    await session.start()
    
    # Stream audio chunks
    async def audio_stream():
        # Your audio source here
        yield audio_chunk
    
    await session.process_audio_stream(audio_stream())
    await session.stop()

asyncio.run(main())
```

### Voice Gateway Server

```python
import asyncio
from cell0.service.voice_gateway import VoiceGateway, GatewayConfig

async def main():
    config = GatewayConfig(port=18803)
    gateway = VoiceGateway(config)
    await gateway.start()
    
    # Run forever
    await asyncio.Future()

asyncio.run(main())
```

Or use the CLI:

```bash
python -m cell0.service.voice_gateway --port 18803
```

### WebSocket Client Protocol

Connect to `ws://localhost:18803` and send:

```json
// Configuration
{
  "type": "configure",
  "payload": {
    "tts": {"provider": "elevenlabs", "voice": "Rachel"},
    "stt": {"provider": "whisper_api", "language": "en"},
    "wake_word": {"keyword": "hey cell"}
  }
}

// Start listening
{"type": "start_listening"}

// Stop listening
{"type": "stop_listening"}

// Ping
{"type": "ping", "payload": {"timestamp": 1234567890}}
```

Send binary audio data (16kHz, 16-bit, mono PCM) after starting.

Receive messages:

```json
// Ready
{"type": "ready", "payload": {"session_id": "...", "config": {...}}}

// Wake word detected
{"type": "wake_word", "payload": {"keyword": "hey cell", "confidence": 0.95}}

// Transcription
{"type": "transcription", "payload": {"text": "Hello", "confidence": 0.92}}

// State change
{"type": "state_change", "payload": {"old_state": "LISTENING_WAKE", "new_state": "LISTENING_COMMAND"}}

// Error
{"type": "error", "payload": {"message": "..."}}
```

## Testing

```bash
# Run all tests
cd /Users/yigremgetachewtamiru/.openclaw/workspace/cell0
pytest tests/test_voice.py -v

# Run specific test class
pytest tests/test_voice.py::TestTTSConfig -v

# Run with coverage
pytest tests/test_voice.py --cov=engine.voice --cov-report=html
```

## Platform Support

| Feature | macOS | Linux | Notes |
|---------|-------|-------|-------|
| TTS (ElevenLabs) | ✓ | ✓ | Requires API key |
| TTS (say) | ✓ | ✗ | macOS native |
| TTS (espeak) | ✗ | ✓ | Install espeak |
| STT (Whisper API) | ✓ | ✓ | Requires API key |
| STT (whisper.cpp) | ✓ | ✓ | Build from source |
| STT (local whisper) | ✓ | ✓ | pip install |
| Wake Word (Porcupine) | ✓ | ✓ | Requires access key |
| Wake Word (VAD) | ✓ | ✓ | Always available |
| Audio Playback | ✓ | ✓ | afplay/aplay/PyAudio |

## Configuration

Environment variables:

```bash
# API Keys (fallback if 1Password not available)
export ELEVENLABS_API_KEY="..."
export OPENAI_API_KEY="..."
export PICOVOICE_ACCESS_KEY="..."

# whisper.cpp paths
export WHISPER_CPP_PATH="/path/to/whisper-cli"
export WHISPER_MODEL_PATH="/path/to/ggml-base.bin"
```

## Troubleshooting

### No audio output
- Check audio player availability: `which afplay` (macOS) or `which aplay` (Linux)
- Install PyAudio: `pip install pyaudio`

### Wake word not detected
- Check microphone input levels
- Try adjusting VAD threshold
- Use quieter environment

### STT not working
- Verify API key in 1Password or environment
- For whisper.cpp, ensure model file exists
- Check audio format (must be 16kHz, 16-bit, mono)

### High latency
- Enable streaming mode in config
- Use whisper.cpp for local processing
- Check network connection for API calls

## License

Part of Cell 0 OS - Sovereign Edge Model OS
