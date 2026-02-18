#!/usr/bin/env python3
"""
Voice Integration Example for Cell 0 OS
Demonstrates TTS, STT, wake word detection, and voice sessions
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cell0.engine.voice import (
    TTSManager, TTSConfig, TTSProvider,
    STTManager, STTConfig,
    WakeWordManager, WakeWordConfig,
    VoiceSession, VoiceSessionConfig, SessionState
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_tts():
    """Demonstrate text-to-speech"""
    print("\n=== TTS Demo ===")
    
    manager = TTSManager()
    
    # Show available providers
    providers = manager.list_available_providers()
    print(f"Available TTS providers: {[p.value for p in providers]}")
    print(f"Current provider: {manager.current_provider.__class__.__name__}")
    
    # Speak some text
    text = "Hello, I am Cell 0. Your sovereign edge voice assistant."
    print(f"Speaking: {text}")
    
    await manager.play(text)
    await manager.close()
    
    print("TTS demo complete")


async def demo_stt(audio_path: Path = None):
    """Demonstrate speech-to-text"""
    print("\n=== STT Demo ===")
    
    manager = STTManager()
    
    # Show available providers
    providers = manager.list_available_providers()
    print(f"Available STT providers: {[p.value for p in providers]}")
    print(f"Current provider: {manager.current_provider.__class__.__name__}")
    
    if audio_path and audio_path.exists():
        print(f"Transcribing: {audio_path}")
        result = await manager.transcribe(audio_path)
        print(f"Transcription: {result.text}")
        if result.confidence:
            print(f"Confidence: {result.confidence:.2%}")
    else:
        print("No audio file provided, skipping transcription")
    
    await manager.close()
    print("STT demo complete")


async def demo_wake_word():
    """Demonstrate wake word detection"""
    print("\n=== Wake Word Demo ===")
    
    manager = WakeWordManager()
    
    # Show available providers
    providers = manager.list_available_providers()
    print(f"Available wake word providers: {[p.value for p in providers]}")
    print(f"Current provider: {manager.current_provider.__class__.__name__}")
    print(f"Configured keyword: {manager.config.keyword}")
    
    print("\nWake word demo: Would listen for wake word in a real scenario")
    print("Simulating wake word detection...")
    
    await manager.close()
    print("Wake word demo complete")


async def demo_voice_session():
    """Demonstrate complete voice session"""
    print("\n=== Voice Session Demo ===")
    
    # Track session events
    events = []
    
    def on_wake(event):
        events.append(f"Wake: {event.keyword}")
        print(f"🔔 Wake word detected: {event.keyword}")
    
    def on_command(result):
        events.append(f"Command: {result.text}")
        print(f"🎤 Command: {result.text}")
    
    def on_response(text):
        events.append(f"Response: {text}")
        print(f"🔊 Response: {text}")
    
    def on_state_change(old, new):
        print(f"📊 State: {old.name} -> {new.name}")
    
    config = VoiceSessionConfig(
        on_wake_word=on_wake,
        on_command=on_command,
        on_response=on_response,
        on_state_change=on_state_change,
        continuous_mode=False  # Single interaction
    )
    
    session = VoiceSession(config)
    
    print("Starting voice session...")
    await session.start()
    
    # Simulate the flow
    print("\nSimulating voice interaction flow:")
    
    # 1. Start listening for wake word
    print("\n1. Session is LISTENING_WAKE")
    await asyncio.sleep(0.5)
    
    # 2. Simulate wake word detection
    print("2. Wake word detected!")
    config.on_wake_word(None)  # Would be a real WakeWordEvent
    
    # 3. Now listening for command
    print("3. Session is LISTENING_COMMAND")
    await asyncio.sleep(0.5)
    
    # 4. Simulate command transcription
    print("4. Command received")
    mock_result = type('obj', (object,), {
        'text': 'What time is it?',
        'confidence': 0.95
    })()
    config.on_command(mock_result)
    
    # 5. Processing
    print("5. Processing...")
    session._set_state(SessionState.PROCESSING)
    await asyncio.sleep(0.5)
    
    # 6. Speaking response
    print("6. Speaking response...")
    session._set_state(SessionState.SPEAKING)
    config.on_response("The current time is 3:45 PM")
    
    # Stop session
    await session.stop()
    
    print(f"\nSession events: {events}")
    print("Voice session demo complete")


async def run_gateway():
    """Run the voice gateway server"""
    print("\n=== Voice Gateway ===")
    print("Starting WebSocket gateway on port 18803...")
    
    from cell0.service.voice_gateway import VoiceGateway, GatewayConfig
    
    config = GatewayConfig(port=18803)
    gateway = VoiceGateway(config)
    
    await gateway.start()
    
    print("Gateway running. Press Ctrl+C to stop.")
    
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\nStopping gateway...")
    finally:
        await gateway.stop()


async def main():
    parser = argparse.ArgumentParser(description="Cell 0 Voice Integration Demo")
    parser.add_argument(
        "--demo",
        choices=["tts", "stt", "wake", "session", "gateway", "all"],
        default="all",
        help="Which demo to run"
    )
    parser.add_argument(
        "--audio",
        type=Path,
        help="Audio file for STT demo"
    )
    
    args = parser.parse_args()
    
    demos = {
        "tts": demo_tts,
        "stt": lambda: demo_stt(args.audio),
        "wake": demo_wake_word,
        "session": demo_voice_session,
        "gateway": run_gateway
    }
    
    if args.demo == "all":
        # Run all demos except gateway
        for name, demo_fn in demos.items():
            if name != "gateway":
                await demo_fn()
                await asyncio.sleep(1)  # Pause between demos
    else:
        await demos[args.demo]()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
