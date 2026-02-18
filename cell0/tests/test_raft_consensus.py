#!/usr/bin/env python3
"""
Cell0 Raft Consensus Test Suite
Tests the distributed consensus implementation.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cell0.service.raft_consensus import (
    RaftConsensusService, RaftConfig, RaftState, LogEntry
)


async def test_single_node():
    """Test single node cluster."""
    print("\n=== Test: Single Node Cluster ===")
    
    config = RaftConfig(
        node_id=1,
        peers=[],
        data_dir=Path("/tmp/cell0_raft_test_single")
    )
    
    service = RaftConsensusService(config)
    
    # Simulate election timeout
    await service._start_election()
    
    assert service.is_leader(), "Single node should become leader"
    assert service.state == RaftState.LEADER
    
    # Propose a command
    entry = await service.propose(b"test_command")
    assert entry is not None, "Should be able to propose as leader"
    assert entry.term == 1
    assert entry.index == 1
    
    print(f"✓ Single node became leader: {service.get_status()}")
    return True


async def test_vote_granting():
    """Test vote granting logic."""
    print("\n=== Test: Vote Granting ===")
    
    config = RaftConfig(
        node_id=1,
        peers=[2, 3],
        data_dir=Path("/tmp/cell0_raft_test_vote")
    )
    
    service = RaftConsensusService(config)
    
    # Request vote with higher term
    response = await service.handle_request_vote(
        term=1,
        candidate_id=2,
        last_log_index=0,
        last_log_term=0
    )
    
    assert response['vote_granted'], "Should grant vote to valid candidate"
    assert service.voted_for == 2
    
    print(f"✓ Vote granted: {response}")
    return True


async def test_log_replication():
    """Test log replication."""
    print("\n=== Test: Log Replication ===")
    
    config = RaftConfig(
        node_id=1,
        peers=[2, 3],
        data_dir=Path("/tmp/cell0_raft_test_log")
    )
    
    service = RaftConsensusService(config)
    
    # Become leader
    await service._become_leader()
    
    # Propose multiple entries
    entries = []
    for i in range(5):
        entry = await service.propose(f"command_{i}".encode())
        entries.append(entry)
    
    assert len(service.log) == 5, "Should have 5 log entries"
    assert service._last_log_index() == 5
    
    print(f"✓ Log replication: {len(service.log)} entries")
    return True


async def test_append_entries():
    """Test AppendEntries RPC handling."""
    print("\n=== Test: AppendEntries RPC ===")
    
    config = RaftConfig(
        node_id=2,  # Follower
        peers=[1, 3],
        data_dir=Path("/tmp/cell0_raft_test_append")
    )
    
    service = RaftConsensusService(config)
    
    # Send valid heartbeat
    response = await service.handle_append_entries(
        term=1,
        leader_id=1,
        prev_log_index=0,
        prev_log_term=0,
        entries=[],
        leader_commit=0
    )
    
    assert response['success'], "Should accept valid heartbeat"
    assert service.leader_id == 1
    
    # Send entries
    entry = LogEntry(term=1, index=1, data=b"test", entry_type="command")
    response = await service.handle_append_entries(
        term=1,
        leader_id=1,
        prev_log_index=0,
        prev_log_term=0,
        entries=[entry.to_bytes()],
        leader_commit=1
    )
    
    assert response['success'], "Should accept valid entries"
    assert len(service.log) == 1
    
    print(f"✓ AppendEntries handling works")
    return True


async def test_quorum_calculation():
    """Test quorum calculation."""
    print("\n=== Test: Quorum Calculation ===")
    
    test_cases = [
        (1, 1),  # Single node
        (2, 2),  # 2 nodes
        (3, 2),  # 3 nodes
        (5, 3),  # 5 nodes
        (7, 4),  # 7 nodes
    ]
    
    for cluster_size, expected_quorum in test_cases:
        peers = list(range(2, cluster_size + 1))
        config = RaftConfig(
            node_id=1,
            peers=peers,
            data_dir=Path(f"/tmp/cell0_raft_test_quorum_{cluster_size}")
        )
        service = RaftConsensusService(config)
        
        assert service._quorum() == expected_quorum, \
            f"Cluster size {cluster_size} should have quorum {expected_quorum}"
    
    print(f"✓ Quorum calculation correct")
    return True


async def test_state_transitions():
    """Test state transitions."""
    print("\n=== Test: State Transitions ===")
    
    state_changes = []
    
    def on_state_change(old, new):
        state_changes.append((old, new))
    
    config = RaftConfig(
        node_id=1,
        peers=[2, 3],
        data_dir=Path("/tmp/cell0_raft_test_state")
    )
    
    service = RaftConsensusService(config)
    service.on_state_change = on_state_change
    
    # Start as follower
    assert service.state == RaftState.FOLLOWER
    
    # Become candidate
    await service._start_election()
    assert service.state == RaftState.CANDIDATE
    
    # Become leader
    await service._become_leader()
    assert service.state == RaftState.LEADER
    
    print(f"✓ State transitions: {state_changes}")
    return True


async def test_log_entry_serialization():
    """Test log entry serialization."""
    print("\n=== Test: Log Entry Serialization ===")
    
    entry = LogEntry(
        term=5,
        index=100,
        data=b"test data content",
        entry_type="command"
    )
    
    # Serialize
    serialized = entry.to_bytes()
    assert len(serialized) > 0
    
    # Deserialize
    restored = LogEntry.from_bytes(serialized)
    
    assert restored.term == entry.term
    assert restored.index == entry.index
    assert restored.data == entry.data
    assert restored.entry_type == entry.entry_type
    
    print(f"✓ Log entry serialization works")
    return True


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Cell0 Raft Consensus Test Suite")
    print("=" * 60)
    
    tests = [
        test_single_node,
        test_vote_granting,
        test_log_replication,
        test_append_entries,
        test_quorum_calculation,
        test_state_transitions,
        test_log_entry_serialization,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if await test():
                passed += 1
            else:
                failed += 1
                print(f"✗ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} error: {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
