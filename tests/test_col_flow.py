"""
COL-Flow Module Tests
Cell 0 OS - Cognitive Operating Layer

Tests for the flow governance and conversation management module.
"""

import pytest
import time
import asyncio
from typing import List, Set, Dict, Any

# Import modules to test
import sys
sys.path.insert(0, '.')

from col.flow.extractor import (
    RequestExtractor, ExtractedRequest, ExtractionResult,
    RequestType, RequestPriority, extract_requests
)
from col.flow.scheduler import (
    RequestScheduler, AsyncRequestScheduler, ScheduledRequest,
    SchedulePlan, RequestStatus, ScheduleStrategy
)
from col.flow.pressure import (
    PressureManager, AdaptivePressureManager,
    PressureLevel, PressureDimension, ConversationSummary
)
from col.flow.visualizer import (
    FlowVisualizer, FlowNode, FlowEdge, NodeType, EdgeType, NodeStatus,
    PressureVisualizer, create_flow
)
from col.flow.interrupt import (
    InterruptHandler, LongRunningTaskManager,
    Interrupt, InterruptType, InterruptPriority, Checkpoint
)


# ============================================================================
# Extractor Tests
# ============================================================================

class TestRequestExtractor:
    """Tests for the RequestExtractor."""
    
    def test_extract_single_request(self):
        """Test extracting a single request."""
        extractor = RequestExtractor()
        result = extractor.extract("What is the weather today?")
        
        assert isinstance(result, ExtractionResult)
        assert len(result.requests) == 1
        assert result.requests[0].type == RequestType.QUESTION
        assert not result.has_multiple
    
    def test_extract_multiple_requests(self):
        """Test extracting multiple requests."""
        extractor = RequestExtractor()
        result = extractor.extract(
            "What is the weather today? Also, can you write a poem about rain?"
        )
        
        assert result.has_multiple
        assert len(result.requests) >= 2
    
    def test_extract_from_list(self):
        """Test extracting from a list format."""
        extractor = RequestExtractor()
        result = extractor.extract("""
            1. Check my email
            2. Summarize the news
            3. Set a reminder
        """)
        
        assert len(result.requests) >= 3
    
    def test_request_type_detection(self):
        """Test request type detection."""
        extractor = RequestExtractor()
        
        tests = [
            ("What is Python?", RequestType.QUESTION),
            ("Run the script", RequestType.ACTION),
            ("Write a function", RequestType.CREATION),
            ("Analyze this data", RequestType.ANALYSIS),
            ("Compare A and B", RequestType.COMPARISON),
        ]
        
        for text, expected_type in tests:
            result = extractor.extract(text)
            assert result.requests[0].type == expected_type, f"Failed for: {text}"
    
    def test_priority_detection(self):
        """Test priority detection from text."""
        extractor = RequestExtractor()
        
        # High priority
        result = extractor.extract("URGENT: Fix the server crash!")
        assert result.requests[0].priority == RequestPriority.CRITICAL
        
        # Low priority
        result = extractor.extract("When you get a chance, clean up the files")
        assert result.requests[0].priority == RequestPriority.LOW
    
    def test_dependency_detection(self):
        """Test detecting dependencies between requests."""
        extractor = RequestExtractor()
        result = extractor.extract(
            "Create a file. Then read it and tell me what's inside."
        )
        
        # Should detect that second request depends on first
        if len(result.requests) >= 2:
            # Find the read request
            read_req = next(
                (r for r in result.requests if 'read' in r.content.lower()),
                None
            )
            if read_req:
                assert len(read_req.dependencies) > 0
    
    def test_empty_input(self):
        """Test handling empty input."""
        extractor = RequestExtractor()
        result = extractor.extract("")
        
        assert len(result.requests) == 0
        assert not result.has_multiple
    
    def test_quick_extract(self):
        """Test quick extract convenience function."""
        requests = RequestExtractor().quick_extract(
            "Task 1 and task 2"
        )
        
        assert isinstance(requests, list)
        assert len(requests) > 0


# ============================================================================
# Scheduler Tests
# ============================================================================

class TestRequestScheduler:
    """Tests for the RequestScheduler."""
    
    def test_add_request(self):
        """Test adding a request."""
        scheduler = RequestScheduler()
        req = scheduler.add_request(
            request_id="test_1",
            content="Test request",
            priority=1
        )
        
        assert req.request_id == "test_1"
        assert req.status == RequestStatus.QUEUED
    
    def test_add_with_dependencies(self):
        """Test adding requests with dependencies."""
        scheduler = RequestScheduler()
        
        req1 = scheduler.add_request("req_1", "First task")
        req2 = scheduler.add_request(
            "req_2",
            "Second task",
            dependencies={"req_1"}
        )
        
        assert req2.status == RequestStatus.BLOCKED
        assert "req_1" in req2.dependencies
    
    def test_dependency_resolution(self):
        """Test that dependencies are resolved correctly."""
        scheduler = RequestScheduler()
        
        scheduler.add_request("req_1", "First task")
        scheduler.add_request("req_2", "Second task", dependencies={"req_1"})
        
        # Complete first request
        scheduler.mark_completed("req_1")
        
        # Second should now be queued
        req2 = scheduler._requests["req_2"]
        assert req2.status == RequestStatus.QUEUED
    
    def test_priority_ordering(self):
        """Test that priority affects ordering."""
        scheduler = RequestScheduler(strategy=ScheduleStrategy.PRIORITY)
        
        scheduler.add_request("low", "Low priority", priority=3)
        scheduler.add_request("high", "High priority", priority=0)
        scheduler.add_request("med", "Medium priority", priority=2)
        
        # Get next should return highest priority
        next_req = scheduler.get_next()
        assert next_req.request_id == "high"
    
    def test_create_plan(self):
        """Test creating an execution plan."""
        scheduler = RequestScheduler()
        
        scheduler.add_request("req_1", "Task 1")
        scheduler.add_request("req_2", "Task 2", dependencies={"req_1"})
        scheduler.add_request("req_3", "Task 3")
        
        plan = scheduler.create_plan()
        
        assert isinstance(plan, SchedulePlan)
        assert len(plan.order) == 3
        assert "req_1" in plan.order
        # req_2 should come after req_1
        assert plan.order.index("req_2") > plan.order.index("req_1")
    
    def test_parallel_groups(self):
        """Test identifying parallel execution groups."""
        scheduler = RequestScheduler()
        
        # Add independent requests
        scheduler.add_request("req_1", "Task 1")
        scheduler.add_request("req_2", "Task 2")
        scheduler.add_request("req_3", "Task 3", dependencies={"req_1", "req_2"})
        
        plan = scheduler.create_plan()
        
        # First group should have req_1 and req_2
        assert len(plan.parallel_groups) >= 2
    
    def test_mark_failed_propagation(self):
        """Test that failure propagates to dependents."""
        scheduler = RequestScheduler()
        
        scheduler.add_request("req_1", "Task 1")
        scheduler.add_request("req_2", "Task 2", dependencies={"req_1"})
        scheduler.add_request("req_3", "Task 3", dependencies={"req_2"})
        
        scheduler.mark_failed("req_1", "Error occurred")
        
        assert scheduler._requests["req_2"].status == RequestStatus.FAILED
        assert scheduler._requests["req_3"].status == RequestStatus.FAILED
    
    def test_cancel_request(self):
        """Test cancelling a request."""
        scheduler = RequestScheduler()
        
        scheduler.add_request("req_1", "Task 1")
        scheduler.add_request("req_2", "Task 2", dependencies={"req_1"})
        
        scheduler.mark_cancelled("req_1")
        
        assert scheduler._requests["req_1"].status == RequestStatus.CANCELLED
        assert scheduler._requests["req_2"].status == RequestStatus.CANCELLED


class TestAsyncRequestScheduler:
    """Tests for the AsyncRequestScheduler."""
    
    @pytest.mark.asyncio
    async def test_async_execution(self):
        """Test async request execution."""
        scheduler = AsyncRequestScheduler()
        
        results = []
        
        async def executor(req):
            await asyncio.sleep(0.01)
            results.append(req.request_id)
            return f"Result for {req.request_id}"
        
        scheduler.add_request("req_1", "Task 1", executor=executor)
        
        await scheduler.execute_next()
        
        assert "req_1" in results
        assert scheduler._requests["req_1"].status == RequestStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel execution of requests."""
        scheduler = AsyncRequestScheduler(max_parallel=3)
        
        execution_order = []
        
        async def executor(req):
            execution_order.append((req.request_id, time.time()))
            await asyncio.sleep(0.05)
            return req.request_id
        
        # Add multiple requests
        for i in range(3):
            scheduler.add_request(f"req_{i}", f"Task {i}", executor=executor)
        
        # Execute all
        await scheduler.execute_all()
        
        # All should be completed
        for i in range(3):
            assert scheduler._requests[f"req_{i}"].status == RequestStatus.COMPLETED


# ============================================================================
# Pressure Tests
# ============================================================================

class TestPressureManager:
    """Tests for the PressureManager."""
    
    def test_initial_state(self):
        """Test initial pressure state."""
        manager = PressureManager()
        snapshot = manager.check_pressure()
        
        assert snapshot.overall_level == PressureLevel.NORMAL
        assert len(snapshot.readings) == len(PressureDimension)
    
    def test_token_pressure(self):
        """Test token count pressure."""
        manager = PressureManager(
            soft_token_limit=100,
            hard_token_limit=200
        )
        
        # Normal
        manager.update_tokens(50)
        snapshot = manager.check_pressure()
        assert snapshot.overall_level == PressureLevel.NORMAL
        
        # Elevated
        manager.update_tokens(80)
        snapshot = manager.check_pressure()
        assert snapshot.overall_level == PressureLevel.ELEVATED
        
        # High
        manager.update_tokens(170)
        snapshot = manager.check_pressure()
        assert snapshot.overall_level == PressureLevel.HIGH
        
        # Critical
        manager.update_tokens(210)
        snapshot = manager.check_pressure()
        assert snapshot.overall_level == PressureLevel.CRITICAL
    
    def test_should_summarize(self):
        """Test summarization trigger."""
        manager = PressureManager(
            hard_token_limit=100
        )
        
        assert not manager.should_summarize()
        
        manager.update_tokens(90)
        assert manager.should_summarize()
    
    def test_create_summary(self):
        """Test creating a conversation summary."""
        manager = PressureManager()
        
        summary = manager.create_summary(
            key_points=["Point 1", "Point 2"],
            decisions_made=["Decision A"],
            action_items=["Action 1"],
            token_savings=500
        )
        
        assert isinstance(summary, ConversationSummary)
        assert len(summary.key_points) == 2
        assert summary.token_savings == 500
    
    def test_recommendations(self):
        """Test that recommendations are generated."""
        manager = PressureManager(
            hard_token_limit=100
        )
        
        manager.update_tokens(90)
        snapshot = manager.check_pressure()
        
        assert len(snapshot.recommendations) > 0
        assert any("summarizing" in r.lower() for r in snapshot.recommendations)
    
    def test_get_trend(self):
        """Test pressure trend calculation."""
        manager = PressureManager(
            hard_token_limit=100
        )
        
        # Simulate increasing pressure
        for tokens in [10, 20, 30, 40, 50]:
            manager.update_tokens(tokens)
            manager.check_pressure()
        
        trend, description = manager.get_pressure_trend()
        
        assert description in ["increasing", "stable"]
    
    def test_stats(self):
        """Test getting statistics."""
        manager = PressureManager()
        
        manager.update_tokens(100)
        manager.increment_turn()
        manager.add_topic("Python")
        
        stats = manager.get_stats()
        
        assert stats['current_tokens'] == 100
        assert stats['turn_count'] == 1
        assert stats['topic_count'] == 1


class TestAdaptivePressureManager:
    """Tests for the AdaptivePressureManager."""
    
    def test_adaptation(self):
        """Test that limits adapt based on usage."""
        manager = AdaptivePressureManager()
        manager._adaptation_enabled = True
        
        # Record high usage pattern
        for _ in range(15):
            manager.record_usage(tokens_used=600, duration=1.0)
        
        # Trigger adaptation
        manager.adapt_limits()
        
        # Limits should have increased
        soft, hard = manager.limits[PressureDimension.TOKEN_COUNT]
        assert soft >= 6000  # Default was 6000


# ============================================================================
# Visualizer Tests
# ============================================================================

class TestFlowVisualizer:
    """Tests for the FlowVisualizer."""
    
    def test_add_node(self):
        """Test adding nodes."""
        viz = FlowVisualizer()
        node = viz.add_node(
            node_id="node_1",
            node_type=NodeType.REQUEST,
            label="Test Node"
        )
        
        assert node.id == "node_1"
        assert node.type == NodeType.REQUEST
        assert node.status == NodeStatus.PENDING
    
    def test_add_edge(self):
        """Test adding edges."""
        viz = FlowVisualizer()
        
        viz.add_node("a", NodeType.REQUEST, "A")
        viz.add_node("b", NodeType.REQUEST, "B")
        edge = viz.add_edge("a", "b", EdgeType.DEPENDENCY)
        
        assert edge.source == "a"
        assert edge.target == "b"
        assert len(viz._edges) == 1
    
    def test_update_status(self):
        """Test updating node status."""
        viz = FlowVisualizer()
        viz.add_node("node_1", NodeType.REQUEST, "Test")
        
        viz.update_node_status("node_1", NodeStatus.COMPLETED)
        
        assert viz._nodes["node_1"].status == NodeStatus.COMPLETED
    
    def test_render_ascii(self):
        """Test ASCII rendering."""
        viz = FlowVisualizer()
        viz.add_node("a", NodeType.REQUEST, "First")
        viz.add_node("b", NodeType.REQUEST, "Second")
        viz.add_edge("a", "b")
        
        ascii_output = viz.render_ascii()
        
        assert "First" in ascii_output
        assert "Second" in ascii_output
    
    def test_render_mermaid(self):
        """Test Mermaid diagram generation."""
        viz = FlowVisualizer()
        viz.add_node("a", NodeType.REQUEST, "Node A")
        viz.add_node("b", NodeType.REQUEST, "Node B")
        viz.add_edge("a", "b")
        
        mermaid = viz.render_mermaid()
        
        assert "flowchart TD" in mermaid
        assert "a[" in mermaid
        assert "b[" in mermaid
        assert "a --> b" in mermaid
    
    def test_render_json(self):
        """Test JSON rendering."""
        viz = FlowVisualizer()
        viz.add_node("node_1", NodeType.REQUEST, "Test")
        
        json_output = viz.render_json()
        
        assert "nodes" in json_output
        assert "edges" in json_output
        assert len(json_output["nodes"]) == 1
    
    def test_render_summary(self):
        """Test summary rendering."""
        viz = FlowVisualizer()
        viz.add_node("a", NodeType.REQUEST, "Task A", NodeStatus.COMPLETED)
        viz.add_node("b", NodeType.REQUEST, "Task B", NodeStatus.PENDING)
        
        summary = viz.render_summary()
        
        assert "FLOW STATE SUMMARY" in summary
        assert "Completed" in summary
        assert "Task A" in summary
    
    def test_empty_flow(self):
        """Test rendering empty flow."""
        viz = FlowVisualizer()
        
        ascii_output = viz.render_ascii()
        assert "Empty" in ascii_output or ascii_output == ""


class TestPressureVisualizer:
    """Tests for the PressureVisualizer."""
    
    def test_render_gauge(self):
        """Test pressure gauge rendering."""
        viz = PressureVisualizer()
        
        gauge = viz.render_gauge(0.5, width=20)
        
        assert "[" in gauge
        assert "]" in gauge
        assert "50%" in gauge
    
    def test_render_multi_gauge(self):
        """Test multiple gauge rendering."""
        viz = PressureVisualizer()
        
        readings = {
            'tokens': 0.8,
            'turns': 0.3,
        }
        
        output = viz.render_multi_gauge(readings, width=20)
        
        assert "tokens" in output
        assert "80%" in output


# ============================================================================
# Interrupt Tests
# ============================================================================

class TestInterruptHandler:
    """Tests for the InterruptHandler."""
    
    def test_start_session(self):
        """Test starting a session."""
        handler = InterruptHandler()
        session = handler.start_session()
        
        assert session.id is not None
        assert session.is_active
    
    def test_create_checkpoint(self):
        """Test creating checkpoints."""
        handler = InterruptHandler()
        handler.start_session()
        
        checkpoint = handler.create_checkpoint(
            flow_state={'test': 'data'},
            request_queue=['req_1'],
            completed_requests={'req_0'},
            context={'user': 'test'}
        )
        
        assert isinstance(checkpoint, Checkpoint)
        assert checkpoint.flow_state['test'] == 'data'
    
    def test_interrupt_creation(self):
        """Test creating interrupts."""
        handler = InterruptHandler()
        handler.start_session()
        
        interrupt = handler.interrupt(
            InterruptType.USER,
            "user_input",
            "User wants to pause",
            InterruptPriority.HIGH
        )
        
        assert interrupt.type == InterruptType.USER
        assert interrupt.priority == InterruptPriority.HIGH
        assert not handler._session.is_active
    
    def test_get_next_interrupt(self):
        """Test interrupt queue ordering."""
        handler = InterruptHandler()
        handler.start_session()
        
        handler.interrupt(InterruptType.USER, "test", "Low", InterruptPriority.LOW)
        handler.interrupt(InterruptType.SYSTEM, "test", "Critical", InterruptPriority.CRITICAL)
        handler.interrupt(InterruptType.USER, "test", "Normal", InterruptPriority.NORMAL)
        
        next_int = handler.get_next_interrupt()
        
        # Should get highest priority first
        assert next_int.priority == InterruptPriority.CRITICAL
    
    def test_resume(self):
        """Test resuming from checkpoint."""
        handler = InterruptHandler()
        handler.start_session()
        
        handler.create_checkpoint(
            flow_state={'step': 1},
            request_queue=['req_1'],
            completed_requests=set(),
            context={}
        )
        
        handler.interrupt(InterruptType.USER, "test", "Pause")
        
        checkpoint = handler.resume()
        
        assert checkpoint is not None
        assert handler._session.is_active
    
    def test_get_resume_options(self):
        """Test getting resume options."""
        handler = InterruptHandler()
        handler.start_session()
        
        handler.create_checkpoint(
            flow_state={'step': 1},
            request_queue=['req_1'],
            completed_requests=set(),
            context={},
            metadata={'description': 'First checkpoint'}
        )
        
        options = handler.get_resume_options()
        
        assert len(options) == 1
        assert options[0]['description'] == 'First checkpoint'
    
    def test_save_load_session(self):
        """Test session serialization."""
        handler = InterruptHandler()
        handler.start_session(session_id="test_session")
        
        handler.create_checkpoint(
            flow_state={'data': 'test'},
            request_queue=['req_1'],
            completed_requests={'req_0'},
            context={'key': 'value'}
        )
        
        saved = handler.save_session()
        
        # Load into new handler
        new_handler = InterruptHandler()
        new_handler.load_session(saved)
        
        assert new_handler._session.id == "test_session"
        assert len(new_handler._session.checkpoints) == 1
    
    def test_can_resume(self):
        """Test can_resume check."""
        handler = InterruptHandler()
        
        assert not handler.can_resume()
        
        handler.start_session()
        handler.create_checkpoint(
            flow_state={},
            request_queue=[],
            completed_requests=set(),
            context={}
        )
        handler.interrupt(InterruptType.USER, "test", "Pause")
        
        assert handler.can_resume()


class TestLongRunningTaskManager:
    """Tests for the LongRunningTaskManager."""
    
    def test_start_task(self):
        """Test starting a task."""
        manager = LongRunningTaskManager()
        task = manager.start_task("task_1", "Test task", total_steps=10)
        
        assert task['id'] == "task_1"
        assert task['total_steps'] == 10
        assert task['status'] == 'running'
    
    def test_update_progress(self):
        """Test updating task progress."""
        manager = LongRunningTaskManager()
        manager.start_task("task_1", "Test task", total_steps=10)
        
        manager.update_progress("task_1", 5)
        
        progress = manager.get_task_progress("task_1")
        assert progress['current_step'] == 5
        assert progress['progress'] == 0.5
    
    def test_complete_task(self):
        """Test completing a task."""
        manager = LongRunningTaskManager()
        manager.start_task("task_1", "Test task")
        
        manager.complete_task("task_1", result="Done!")
        
        task = manager._tasks["task_1"]
        assert task['status'] == 'completed'
        assert task['result'] == "Done!"
    
    def test_fail_task(self):
        """Test failing a task."""
        manager = LongRunningTaskManager()
        manager.start_task("task_1", "Test task")
        
        manager.fail_task("task_1", "Error occurred")
        
        task = manager._tasks["task_1"]
        assert task['status'] == 'failed'
        assert 'Error occurred' in task['error']
    
    def test_progress_bar(self):
        """Test progress bar formatting."""
        manager = LongRunningTaskManager()
        manager.start_task("task_1", "Test task", total_steps=10)
        manager.update_progress("task_1", 5)
        
        bar = manager.format_progress_bar("task_1", width=20)
        
        assert "Test task" in bar
        assert "50.0%" in bar
        assert "[" in bar and "]" in bar


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the full COL-Flow system."""
    
    def test_full_flow(self):
        """Test a complete flow from extraction to visualization."""
        # 1. Extract requests
        user_input = """
        1. Check the weather in Tokyo
        2. If it's sunny, suggest outdoor activities
        3. Otherwise, suggest indoor activities
        """
        
        extractor = RequestExtractor()
        extraction = extractor.extract(user_input)
        
        assert len(extraction.requests) >= 2
        
        # 2. Schedule requests
        scheduler = RequestScheduler()
        for i, req in enumerate(extraction.requests):
            scheduler.add_request(
                request_id=req.id,
                content=req.content,
                priority=req.priority.value,
                dependencies=set(req.dependencies)
            )
        
        plan = scheduler.create_plan()
        assert len(plan.order) == len(extraction.requests)
        
        # 3. Check pressure
        pressure = PressureManager()
        pressure.update_tokens(500)
        for _ in range(10):
            pressure.increment_turn()
        
        snapshot = pressure.check_pressure()
        assert snapshot.overall_level in [PressureLevel.NORMAL, PressureLevel.ELEVATED]
        
        # 4. Visualize
        viz = FlowVisualizer()
        for req in extraction.requests:
            viz.add_node(
                req.id,
                NodeType.REQUEST,
                req.content[:30],
                NodeStatus.PENDING
            )
        
        for req in extraction.requests:
            for dep in req.dependencies:
                viz.add_edge(dep, req.id, EdgeType.DEPENDENCY)
        
        ascii_output = viz.render_ascii()
        assert len(ascii_output) > 0
    
    def test_interrupt_and_resume(self):
        """Test interrupt handling and flow resumption."""
        # Setup flow
        handler = InterruptHandler()
        handler.start_session()
        
        # Create initial checkpoint
        handler.create_checkpoint(
            flow_state={'step': 1, 'data': 'initial'},
            request_queue=['req_1', 'req_2'],
            completed_requests=set(),
            context={'user': 'test'}
        )
        
        # Simulate work and interrupt
        handler.create_checkpoint(
            flow_state={'step': 2, 'data': 'processed'},
            request_queue=['req_2'],
            completed_requests={'req_1'},
            context={'user': 'test'}
        )
        
        interrupt = handler.interrupt(
            InterruptType.USER,
            "user",
            "Need to pause"
        )
        
        assert not handler._session.is_active
        
        # Resume
        checkpoint = handler.resume()
        assert handler._session.is_active
        assert checkpoint.flow_state['step'] == 2


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Run with: python -m pytest tests/test_col_flow.py -v
    # Or: python tests/test_col_flow.py
    
    print("COL-Flow Module Tests")
    print("=" * 50)
    print("Run with pytest: pytest tests/test_col_flow.py -v")
    print("=" * 50)