#!/usr/bin/env python3
"""
Quick test script for Cell 0 daemon
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cell0d import Cell0Daemon

async def test_daemon():
    daemon = Cell0Daemon()
    print(f"✓ Daemon created")
    print(f"  - HTTP port: {daemon.http_port}")
    print(f"  - WebSocket port: {daemon.ws_port}")
    print(f"  - Metrics port: {daemon.metrics_port}")
    print(f"  - Environment: {daemon.environment}")
    
    # Test MLX
    print(f"\n✓ MLX Bridge:")
    print(f"  - Available: {daemon.mlx_bridge is not None}")
    
    # Test startup (without running server)
    print(f"\n✓ Testing startup sequence...")
    try:
        await daemon._startup()
        print(f"  - MLX initialized: {daemon.mlx_bridge.is_available()}")
        print(f"  - WebSocket manager ready: {daemon.ws_manager is not None}")
        print(f"\n✓ All tests passed!")
    except Exception as e:
        print(f"  - Error: {e}")
    finally:
        await daemon._shutdown()

if __name__ == "__main__":
    asyncio.run(test_daemon())
