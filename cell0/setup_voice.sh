#!/bin/bash
# Setup script for Cell 0 OS Voice Integration

set -e

echo "🎙️  Setting up Cell 0 OS Voice Integration"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python version: $PYTHON_VERSION"

# Check OS
OS=$(uname -s)
echo -e "${GREEN}✓${NC} Operating system: $OS"

# Check for 1Password CLI
if command -v op &> /dev/null; then
    echo -e "${GREEN}✓${NC} 1Password CLI found"
else
    echo -e "${YELLOW}⚠${NC} 1Password CLI not found. Install from: https://1password.com/downloads/command-line/"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -q aiohttp aiofiles websockets numpy

# Optional dependencies
echo ""
echo "📦 Checking optional dependencies..."

# PyAudio
if pip install -q pyaudio 2>/dev/null; then
    echo -e "${GREEN}✓${NC} PyAudio installed (for low-latency audio)"
else
    echo -e "${YELLOW}⚠${NC} PyAudio not installed. Audio will use system commands."
    if [ "$OS" = "Darwin" ]; then
        echo "   Install with: brew install portaudio && pip install pyaudio"
    else
        echo "   Install with: sudo apt-get install python3-pyaudio"
    fi
fi

# WebRTC VAD
if pip install -q webrtcvad 2>/dev/null; then
    echo -e "${GREEN}✓${NC} WebRTC VAD installed (for voice activity detection)"
else
    echo -e "${YELLOW}⚠${NC} WebRTC VAD not installed. Using fallback energy detection."
fi

# Check platform-specific audio tools
if [ "$OS" = "Darwin" ]; then
    if command -v afplay &> /dev/null; then
        echo -e "${GREEN}✓${NC} afplay found (macOS audio player)"
    fi
    if command -v say &> /dev/null; then
        echo -e "${GREEN}✓${NC} say found (macOS TTS fallback)"
    fi
elif [ "$OS" = "Linux" ]; then
    if command -v aplay &> /dev/null; then
        echo -e "${GREEN}✓${NC} aplay found (Linux audio player)"
    else
        echo -e "${YELLOW}⚠${NC} aplay not found. Install alsa-utils."
    fi
    if command -v espeak &> /dev/null; then
        echo -e "${GREEN}✓${NC} espeak found (Linux TTS fallback)"
    else
        echo -e "${YELLOW}⚠${NC} espeak not found. Install for TTS fallback."
    fi
fi

# Check for API keys
echo ""
echo "🔑 Checking API keys..."

if [ -n "$ELEVENLABS_API_KEY" ]; then
    echo -e "${GREEN}✓${NC} ElevenLabs API key (environment variable)"
elif command -v op &> /dev/null && op item get "ElevenLabs" &>/dev/null; then
    echo -e "${GREEN}✓${NC} ElevenLabs API key (1Password)"
else
    echo -e "${YELLOW}⚠${NC} ElevenLabs API key not found. TTS will use system fallback."
    echo "   Set ELEVENLABS_API_KEY or store in 1Password as 'ElevenLabs'"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✓${NC} OpenAI API key (environment variable)"
elif command -v op &> /dev/null && op item get "OpenAI" &>/dev/null; then
    echo -e "${GREEN}✓${NC} OpenAI API key (1Password)"
else
    echo -e "${YELLOW}⚠${NC} OpenAI API key not found. STT will use local fallback."
    echo "   Set OPENAI_API_KEY or store in 1Password as 'OpenAI'"
fi

# Check for whisper.cpp
if [ -f "$HOME/whisper.cpp/main" ] || [ -f "$HOME/whisper.cpp/whisper-cli" ]; then
    echo -e "${GREEN}✓${NC} whisper.cpp found"
else
    echo -e "${YELLOW}⚠${NC} whisper.cpp not found. Local STT will use Python whisper."
    echo "   Build from: https://github.com/ggerganov/whisper.cpp"
fi

echo ""
echo "============================================"
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Quick start:"
echo "  1. Run demo:        python3 examples/voice_demo.py"
echo "  2. Run tests:       pytest tests/test_voice.py -v"
echo "  3. Start gateway:   python3 -m cell0.service.voice_gateway"
echo ""
echo "WebSocket endpoint: ws://localhost:18803"
echo ""
