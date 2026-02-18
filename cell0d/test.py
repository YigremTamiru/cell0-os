"""
Unit tests for cell0d event streaming system
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from events.eventbus import EventBus, Event, EventType, event_bus
from websocket.server import WebSocketServer


async def test_eventbus():
    """Test EventBus functionality"""
    print("\n=== Testing EventBus ===")
    
    # Create new event bus for testing
    bus = EventBus(max_history=100)
    await bus.start()
    
    received_events = []
    
    def callback(event):
        received_events.append(event)
        print(f"  ✓ Received: {event.type.value}")
    
    # Subscribe to events
    bus.subscribe(EventType.SYSTEM_STATUS, callback)
    bus.subscribe(EventType.CHAT_MESSAGE, callback)
    
    # Emit events
    print("  Emitting test events...")
    await bus.emit(Event(type=EventType.SYSTEM_STATUS, data={"status": "test"}))
    await bus.emit(Event(type=EventType.CHAT_MESSAGE, data={"msg": "hello"}))
    await bus.emit(Event(type=EventType.LOG_STREAM, data={"log": "test"}))  # Not subscribed
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Check results
    assert len(received_events) == 2, f"Expected 2 events, got {len(received_events)}"
    
    # Check history
    history = bus.get_history()
    assert len(history) == 3, f"Expected 3 in history, got {len(history)}"
    
    # Check filtered history
    status_history = bus.get_history(event_type=EventType.SYSTEM_STATUS)
    assert len(status_history) == 1
    
    await bus.stop()
    print("  ✓ EventBus tests passed!")
    return True


async def test_event_types():
    """Test all event types can be created"""
    print("\n=== Testing Event Types ===")
    
    from events.eventbus import (
        create_system_status_event,
        create_chat_message_event,
        create_model_activity_event,
        create_mcic_event,
        create_log_event,
        create_heartbeat_event
    )
    
    # Test each event factory
    events = [
        create_system_status_event("healthy", {"cpu": 50}),
        create_chat_message_event("Hello", "user", "general"),
        create_model_activity_event("loaded", "qwen2.5-7b"),
        create_mcic_event("kernel_started", "kernel_001"),
        create_log_event("INFO", "Test message"),
        create_heartbeat_event("client_1", 1),
    ]
    
    for event in events:
        assert isinstance(event, Event)
        assert event.id is not None
        assert event.timestamp is not None
        print(f"  ✓ {event.type.value}: {event.to_dict()}")
    
    print("  ✓ All event types work!")
    return True


async def test_event_serialization():
    """Test event serialization"""
    print("\n=== Testing Event Serialization ===")
    
    event = Event(
        type=EventType.SYSTEM_STATUS,
        source="test",
        data={"key": "value", "number": 42}
    )
    
    # To dict
    d = event.to_dict()
    assert d["type"] == "system_status"
    assert d["source"] == "test"
    assert d["data"]["key"] == "value"
    print(f"  ✓ to_dict: {d}")
    
    # To JSON
    json_str = event.to_json()
    assert isinstance(json_str, str)
    print(f"  ✓ to_json: {json_str[:100]}...")
    
    # From dict
    restored = Event.from_dict(d)
    assert restored.type == event.type
    assert restored.source == event.source
    print(f"  ✓ from_dict successful")
    
    print("  ✓ Serialization tests passed!")
    return True


async def test_websocket_server():
    """Test WebSocket server starts and stops"""
    print("\n=== Testing WebSocket Server ===")
    
    # Create a test event bus
    from events.eventbus import EventBus
    test_bus = EventBus(max_history=100)
    await test_bus.start()
    
    server = WebSocketServer(host="127.0.0.1", port=18765, event_bus=test_bus)
    
    # Start server
    await server.start()
    print(f"  ✓ Server started on {server.host}:{server.port}")
    
    # Check initial state
    assert server._running == True
    assert len(server.clients) == 0
    print(f"  ✓ Server running, no clients")
    
    # Stop server
    await server.stop()
    print(f"  ✓ Server stopped")
    
    assert server._running == False
    
    # Stop test event bus
    await test_bus.stop()
    
    print("  ✓ WebSocket server tests passed!")
    return True


async def test_daemon():
    """Test daemon starts and stops"""
    print("\n=== Testing Daemon ===")
    
    from core.daemon import CellZeroDaemon
    
    daemon = CellZeroDaemon(ws_host="127.0.0.1", ws_port=18766)
    
    # Start daemon in background
    daemon_task = asyncio.create_task(daemon.start())
    
    # Wait for startup
    await asyncio.sleep(0.5)
    
    print(f"  ✓ Daemon started")
    assert daemon._running == True
    assert daemon.system_state["status"] == "running"
    
    # Test emitting events
    await daemon.emit_chat_message("Test", "test_user")
    await daemon.emit_model_activity("loaded", "test-model")
    print(f"  ✓ Events emitted")
    
    # Check status
    status = daemon.get_status()
    assert "websocket" in status
    assert "event_bus" in status
    print(f"  ✓ Status retrieved: {list(status.keys())}")
    
    # Stop daemon
    await daemon.stop()
    print(f"  ✓ Daemon stopped")
    
    print("  ✓ Daemon tests passed!")
    return True


async def run_all_tests():
    """Run all tests"""
    print("╔═══════════════════════════════════════════════════╗")
    print("║          cell0d Event Streaming Tests             ║")
    print("╚═══════════════════════════════════════════════════╝")
    
    tests = [
        ("EventBus", test_eventbus),
        ("Event Types", test_event_types),
        ("Serialization", test_event_serialization),
        ("WebSocket Server", test_websocket_server),
        ("Daemon", test_daemon),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"  ✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*55)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)