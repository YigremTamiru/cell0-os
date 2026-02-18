"""
COL-Flow Module
Cell 0 OS - Cognitive Operating Layer

Input governance and conversation flow management.

This module manages the flow of conversation without losing coherence:
- Extracts multiple requests from complex inputs
- Schedules and prioritizes request execution
- Monitors context pressure and triggers summarization
- Visualizes flow state
- Handles interrupts and enables resumption
- Manages long-running tasks
"""

from .extractor import (
    RequestExtractor,
    ExtractedRequest,
    ExtractionResult,
    RequestType,
    RequestPriority,
    extract_requests,
    get_extractor,
)

from .scheduler import (
    RequestScheduler,
    AsyncRequestScheduler,
    ScheduledRequest,
    SchedulePlan,
    RequestStatus,
    ScheduleStrategy,
)

from .pressure import (
    PressureManager,
    AdaptivePressureManager,
    PressureSnapshot,
    PressureReading,
    PressureLevel,
    PressureDimension,
    ConversationSummary,
)

from .visualizer import (
    FlowVisualizer,
    FlowNode,
    FlowEdge,
    FlowState,
    NodeType,
    EdgeType,
    NodeStatus,
    PressureVisualizer,
    create_flow,
    visualize_requests,
)

from .interrupt import (
    InterruptHandler,
    LongRunningTaskManager,
    Interrupt,
    InterruptType,
    InterruptPriority,
    Checkpoint,
    FlowSession,
)

__all__ = [
    # Extractor
    'RequestExtractor',
    'ExtractedRequest',
    'ExtractionResult',
    'RequestType',
    'RequestPriority',
    'extract_requests',
    'get_extractor',
    
    # Scheduler
    'RequestScheduler',
    'AsyncRequestScheduler',
    'ScheduledRequest',
    'SchedulePlan',
    'RequestStatus',
    'ScheduleStrategy',
    
    # Pressure
    'PressureManager',
    'AdaptivePressureManager',
    'PressureSnapshot',
    'PressureReading',
    'PressureLevel',
    'PressureDimension',
    'ConversationSummary',
    
    # Visualizer
    'FlowVisualizer',
    'FlowNode',
    'FlowEdge',
    'FlowState',
    'NodeType',
    'EdgeType',
    'NodeStatus',
    'PressureVisualizer',
    'create_flow',
    'visualize_requests',
    
    # Interrupt
    'InterruptHandler',
    'LongRunningTaskManager',
    'Interrupt',
    'InterruptType',
    'InterruptPriority',
    'Checkpoint',
    'FlowSession',
]