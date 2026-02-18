# COL-Flow Module

**Cell 0 OS - Cognitive Operating Layer**

Flow governance and conversation management for maintaining coherence in complex, multi-request interactions.

## Overview

COL-Flow manages the flow of conversation without losing coherence. It handles:

1. **Multi-request extraction** - Identifies multiple requests in complex inputs
2. **Request scheduling** - Prioritizes and sequences request execution
3. **Context pressure management** - Monitors limits and triggers summarization
4. **Flow visualization** - Renders flow state in multiple formats
5. **Interrupt handling** - Manages pauses and enables resumption
6. **Long-running task management** - Tracks progress with checkpointing

## Architecture

```
col/flow/
├── __init__.py       # Package exports
├── extractor.py      # Multi-request extraction
├── scheduler.py      # Request scheduling
├── pressure.py       # Context pressure management
├── visualizer.py     # Flow state visualization
└── interrupt.py      # Interrupt handling
```

## Usage

### Basic Extraction

```python
from col.flow import extract_requests, RequestType

# Extract multiple requests from complex input
result = extract_requests("""
    Can you check my email and also summarize yesterday's meeting notes?
    Also, please remind me about the 3pm call.
""")

for req in result.requests:
    print(f"{req.type.name}: {req.content}")
# QUESTION: Check my email
# CREATION: Summarize yesterday's meeting notes
# ACTION: Remind me about the 3pm call
```

### Scheduling Requests

```python
from col.flow import RequestScheduler, ScheduleStrategy

scheduler = RequestScheduler(max_parallel=3, strategy=ScheduleStrategy.DEPENDENCY)

# Add requests with dependencies
scheduler.add_request("fetch_data", "Fetch user data")
scheduler.add_request("analyze", "Analyze data", dependencies={"fetch_data"})
scheduler.add_request("report", "Generate report", dependencies={"analyze"})

# Create execution plan
plan = scheduler.create_plan()
print(f"Order: {plan.order}")
print(f"Parallel groups: {plan.parallel_groups}")

# Execute
scheduler.mark_running("fetch_data")
scheduler.mark_completed("fetch_data")
```

### Pressure Management

```python
from col.flow import PressureManager

pressure = PressureManager(
    soft_token_limit=6000,
    hard_token_limit=8000
)

# Update state
pressure.update_tokens(7000)
pressure.increment_turn()

# Check pressure
snapshot = pressure.check_pressure()
if snapshot.overall_level.name == "HIGH":
    print("Warning: Approaching context limit")
    print("Recommendations:", snapshot.recommendations)

# Create summary when needed
if pressure.should_summarize():
    summary = pressure.create_summary(
        key_points=["Discussed architecture", "Agreed on approach"],
        action_items=["Implement core module"]
    )
```

### Visualization

```python
from col.flow import FlowVisualizer, NodeType, NodeStatus, EdgeType

viz = FlowVisualizer()

# Add nodes
viz.add_node("req_1", NodeType.REQUEST, "Fetch data", NodeStatus.COMPLETED)
viz.add_node("req_2", NodeType.REQUEST, "Analyze", NodeStatus.ACTIVE)
viz.add_node("req_3", NodeType.REQUEST, "Report", NodeStatus.PENDING)

# Add edges
viz.add_edge("req_1", "req_2", EdgeType.DEPENDENCY)
viz.add_edge("req_2", "req_3", EdgeType.DEPENDENCY)

# Render
print(viz.render_ascii())
print(viz.render_mermaid())  # For Mermaid diagrams
```

### Interrupt Handling

```python
from col.flow import InterruptHandler, InterruptType, InterruptPriority

handler = InterruptHandler()
handler.start_session()

# Create checkpoint
handler.create_checkpoint(
    flow_state={'step': 3},
    request_queue=['req_4', 'req_5'],
    completed_requests={'req_1', 'req_2', 'req_3'},
    context={'user': 'alice'}
)

# Handle interrupt
interrupt = handler.interrupt(
    InterruptType.USER,
    "user",
    "User wants to change topic",
    InterruptPriority.HIGH
)

# Later... resume
if handler.can_resume():
    checkpoint = handler.resume()
    print(f"Resumed from: {checkpoint.id}")
```

### Long-Running Tasks

```python
from col.flow import LongRunningTaskManager

tasks = LongRunningTaskManager(checkpoint_interval=30.0)

# Start task
tasks.start_task("analysis", "Analyzing large dataset", total_steps=100)

# Update progress
for i in range(100):
    tasks.update_progress("analysis", i + 1, state={'records_processed': i * 1000})
    
    if i % 10 == 0:
        print(tasks.format_progress_bar("analysis"))

tasks.complete_task("analysis", result="Analysis complete")
```

## Request Types

- `QUESTION` - Information seeking
- `ACTION` - Do something
- `CREATION` - Create content
- `ANALYSIS` - Analyze data
- `COMPARISON` - Compare options
- `DECISION` - Make a choice
- `CONFIRMATION` - Verify something
- `CLARIFICATION` - Ask for clarity
- `META` - About the conversation itself

## Scheduling Strategies

- `PRIORITY` - Priority-based ordering
- `FIFO` - First in, first out
- `SJF` - Shortest job first
- `DEADLINE` - Earliest deadline first
- `DEPENDENCY` - Dependency-aware (default)

## Pressure Levels

- `NORMAL` - Operating normally
- `ELEVATED` - Approaching soft limits
- `HIGH` - Near hard limits
- `CRITICAL` - At or exceeding limits

## Testing

```bash
# Run all tests
pytest tests/test_col_flow.py -v

# Run specific test class
pytest tests/test_col_flow.py::TestRequestExtractor -v

# Run with coverage
pytest tests/test_col_flow.py --cov=col.flow --cov-report=html
```

## Integration Example

```python
from col.flow import (
    RequestExtractor, RequestScheduler,
    PressureManager, FlowVisualizer,
    InterruptHandler, NodeType, NodeStatus
)

class ConversationFlow:
    def __init__(self):
        self.extractor = RequestExtractor()
        self.scheduler = RequestScheduler()
        self.pressure = PressureManager()
        self.visualizer = FlowVisualizer()
        self.interrupts = InterruptHandler()
        
    def process_input(self, user_input: str):
        # 1. Extract requests
        extraction = self.extractor.extract(user_input)
        
        # 2. Add to scheduler
        for req in extraction.requests:
            self.scheduler.add_request(
                req.id, req.content, 
                req.priority.value,
                set(req.dependencies)
            )
        
        # 3. Check pressure
        self.pressure.increment_turn()
        snapshot = self.pressure.check_pressure()
        
        if snapshot.overall_level.name == "CRITICAL":
            # Summarize and reset
            summary = self.create_summary()
            self.pressure.reset()
        
        # 4. Visualize
        self.update_visualization()
        
        # 5. Execute
        plan = self.scheduler.create_plan()
        return plan
    
    def create_summary(self):
        # Implementation
        pass
    
    def update_visualization(self):
        # Implementation
        pass
```

## License

Part of Cell 0 OS - Cognitive Operating Layer