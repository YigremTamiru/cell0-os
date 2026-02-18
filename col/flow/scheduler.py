"""
COL-Flow Scheduler Module
Cell 0 OS - Cognitive Operating Layer

Request scheduling and prioritization.
Manages execution order and resource allocation for requests.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Callable, Awaitable, Set
from datetime import datetime
import time
from collections import deque


class RequestStatus(Enum):
    """Status of a scheduled request."""
    PENDING = auto()
    QUEUED = auto()
    RUNNING = auto()
    BLOCKED = auto()       # Waiting for dependencies
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class ScheduleStrategy(Enum):
    """Scheduling strategies."""
    PRIORITY = auto()      # Priority-based
    FIFO = auto()          # First in, first out
    SJF = auto()           # Shortest job first
    DEADLINE = auto()      # Earliest deadline first
    DEPENDENCY = auto()    # Dependency-aware


@dataclass
class ScheduledRequest:
    """A request with scheduling metadata."""
    request_id: str
    content: str
    priority: int  # 0-4, 0 is highest
    status: RequestStatus = RequestStatus.PENDING
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    deadline: Optional[float] = None
    estimated_duration: float = 1.0  # seconds
    actual_duration: Optional[float] = None
    executor: Optional[Callable] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulePlan:
    """A plan for executing requests."""
    order: List[str]  # Request IDs in execution order
    parallel_groups: List[Set[str]]  # Groups that can run in parallel
    estimated_total_time: float
    critical_path: List[str]  # Longest dependency chain
    bottlenecks: List[str]  # Resources that limit parallelism


class RequestScheduler:
    """
    Schedules and manages request execution.
    
    Features:
    - Priority-based scheduling
    - Dependency resolution
    - Parallel execution where safe
    - Deadline awareness
    - Dynamic replanning
    """
    
    def __init__(self, max_parallel: int = 3, strategy: ScheduleStrategy = ScheduleStrategy.DEPENDENCY):
        """
        Initialize scheduler.
        
        Args:
            max_parallel: Maximum parallel executions
            strategy: Scheduling strategy
        """
        self.max_parallel = max_parallel
        self.strategy = strategy
        
        # Request storage
        self._requests: Dict[str, ScheduledRequest] = {}
        self._queue: deque = deque()  # Ready to run
        self._running: Set[str] = set()
        self._completed: Set[str] = set()
        
        # Execution tracking
        self._execution_times: Dict[str, float] = {}
        self._stats = {
            'total_scheduled': 0,
            'total_completed': 0,
            'total_failed': 0,
            'avg_wait_time': 0.0,
            'avg_execution_time': 0.0,
        }
        
        # Callbacks
        self._on_status_change: Optional[Callable] = None
    
    def add_request(
        self,
        request_id: str,
        content: str,
        priority: int = 2,
        dependencies: Optional[Set[str]] = None,
        deadline: Optional[float] = None,
        executor: Optional[Callable] = None,
        metadata: Optional[Dict] = None
    ) -> ScheduledRequest:
        """
        Add a request to the scheduler.
        
        Args:
            request_id: Unique request ID
            content: Request content
            priority: Priority (0=highest, 4=lowest)
            dependencies: Set of request IDs this depends on
            deadline: Unix timestamp deadline
            executor: Function to execute request
            metadata: Additional metadata
            
        Returns:
            The created ScheduledRequest
        """
        req = ScheduledRequest(
            request_id=request_id,
            content=content,
            priority=priority,
            dependencies=dependencies or set(),
            deadline=deadline,
            executor=executor,
            metadata=metadata or {}
        )
        
        self._requests[request_id] = req
        self._stats['total_scheduled'] += 1
        
        # Update dependents
        for dep_id in req.dependencies:
            if dep_id in self._requests:
                self._requests[dep_id].dependents.add(request_id)
        
        # Check if ready to queue
        self._update_status(req)
        
        return req
    
    def add_requests(self, requests: List[Dict]) -> List[ScheduledRequest]:
        """Add multiple requests at once."""
        created = []
        for req_dict in requests:
            sr = self.add_request(**req_dict)
            created.append(sr)
        return created
    
    def _update_status(self, req: ScheduledRequest):
        """Update request status based on dependencies."""
        if req.status in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED]:
            return
        
        # Check if dependencies are met
        unmet_deps = req.dependencies - self._completed
        
        if unmet_deps:
            if req.status != RequestStatus.BLOCKED:
                req.status = RequestStatus.BLOCKED
                self._notify_status_change(req)
        else:
            if req.status != RequestStatus.QUEUED:
                req.status = RequestStatus.QUEUED
                self._queue.append(req.request_id)
                self._notify_status_change(req)
    
    def get_next(self) -> Optional[ScheduledRequest]:
        """
        Get the next request to execute.
        
        Returns:
            Next scheduled request or None
        """
        # Re-sort queue based on strategy
        self._sort_queue()
        
        # Find next ready request
        while self._queue:
            req_id = self._queue.popleft()
            req = self._requests.get(req_id)
            
            if req and req.status == RequestStatus.QUEUED:
                # Check parallel limit
                if len(self._running) < self.max_parallel:
                    return req
                else:
                    # Put back in queue
                    self._queue.appendleft(req_id)
                    return None
        
        return None
    
    def _sort_queue(self):
        """Sort queue based on scheduling strategy."""
        if not self._queue:
            return
        
        # Convert to list for sorting
        items = list(self._queue)
        
        if self.strategy == ScheduleStrategy.PRIORITY:
            items.sort(key=lambda rid: (self._requests[rid].priority, self._requests[rid].created_at))
        
        elif self.strategy == ScheduleStrategy.FIFO:
            items.sort(key=lambda rid: self._requests[rid].created_at)
        
        elif self.strategy == ScheduleStrategy.SJF:
            items.sort(key=lambda rid: self._requests[rid].estimated_duration)
        
        elif self.strategy == ScheduleStrategy.DEADLINE:
            # Sort by deadline (None = end of list)
            items.sort(key=lambda rid: (self._requests[rid].deadline or float('inf'), self._requests[rid].priority))
        
        elif self.strategy == ScheduleStrategy.DEPENDENCY:
            # Priority with deadline awareness
            def sort_key(rid):
                req = self._requests[rid]
                # If has deadline, prioritize
                if req.deadline:
                    urgency = (req.deadline - time.time()) / req.estimated_duration
                    return (0, urgency, req.priority)
                return (1, 0, req.priority)
            
            items.sort(key=sort_key)
        
        self._queue = deque(items)
    
    def mark_running(self, request_id: str):
        """Mark a request as running."""
        req = self._requests.get(request_id)
        if req:
            req.status = RequestStatus.RUNNING
            req.started_at = time.time()
            self._running.add(request_id)
            self._notify_status_change(req)
    
    def mark_completed(self, request_id: str, result: Any = None):
        """Mark a request as completed."""
        req = self._requests.get(request_id)
        if req:
            req.status = RequestStatus.COMPLETED
            req.completed_at = time.time()
            req.result = result
            
            if req.started_at:
                req.actual_duration = req.completed_at - req.started_at
                self._execution_times[request_id] = req.actual_duration
            
            self._running.discard(request_id)
            self._completed.add(request_id)
            self._stats['total_completed'] += 1
            
            # Update waiting dependents
            for dep_id in req.dependents:
                if dep_id in self._requests:
                    self._update_status(self._requests[dep_id])
            
            self._notify_status_change(req)
            self._update_stats()
    
    def mark_failed(self, request_id: str, error: str):
        """Mark a request as failed."""
        req = self._requests.get(request_id)
        if req:
            req.status = RequestStatus.FAILED
            req.completed_at = time.time()
            req.error = error
            
            self._running.discard(request_id)
            self._stats['total_failed'] += 1
            
            # Fail dependents too
            for dep_id in req.dependents:
                self.mark_failed(dep_id, f"Dependency {request_id} failed: {error}")
            
            self._notify_status_change(req)
    
    def mark_cancelled(self, request_id: str):
        """Cancel a request."""
        req = self._requests.get(request_id)
        if req and req.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
            req.status = RequestStatus.CANCELLED
            
            if req.request_id in self._queue:
                self._queue.remove(req.request_id)
            
            self._running.discard(request_id)
            
            # Cancel dependents
            for dep_id in req.dependents:
                self.mark_cancelled(dep_id)
            
            self._notify_status_change(req)
    
    def create_plan(self, request_ids: Optional[List[str]] = None) -> SchedulePlan:
        """
        Create an execution plan for the given requests.
        
        Args:
            request_ids: IDs to include (None = all pending)
            
        Returns:
            SchedulePlan
        """
        if request_ids is None:
            request_ids = [
                rid for rid, req in self._requests.items()
                if req.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED]
            ]
        
        # Build dependency graph
        graph = {rid: self._requests[rid].dependencies.copy() for rid in request_ids}
        
        # Topological sort for order
        order = self._topological_sort(graph)
        
        # Find parallel groups
        parallel_groups = self._find_parallel_groups(graph, order)
        
        # Calculate critical path
        critical_path = self._find_critical_path(request_ids)
        
        # Estimate total time
        total_time = sum(
            self._requests[rid].estimated_duration
            for rid in order
        )
        
        # Find bottlenecks (high contention resources)
        bottlenecks = self._identify_bottlenecks(request_ids)
        
        return SchedulePlan(
            order=order,
            parallel_groups=parallel_groups,
            estimated_total_time=total_time,
            critical_path=critical_path,
            bottlenecks=bottlenecks
        )
    
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """Topological sort of dependency graph."""
        in_degree = {node: 0 for node in graph}
        for node, deps in graph.items():
            for dep in deps:
                if dep in graph:
                    in_degree[node] += 1
        
        # Start with nodes that have no dependencies
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            # Sort by priority
            queue = deque(sorted(queue, key=lambda rid: self._requests[rid].priority))
            node = queue.popleft()
            result.append(node)
            
            # Find nodes that depend on this one
            for other, deps in graph.items():
                if node in deps:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)
        
        return result
    
    def _find_parallel_groups(self, graph: Dict[str, Set[str]], order: List[str]) -> List[Set[str]]:
        """Find groups of requests that can run in parallel."""
        if not order:
            return []
        
        groups = []
        current_group = set()
        completed = set()
        
        for rid in order:
            # Check if all dependencies are satisfied
            deps = graph.get(rid, set())
            if deps <= completed:
                current_group.add(rid)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = {rid}
            
            completed.add(rid)
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _find_critical_path(self, request_ids: List[str]) -> List[str]:
        """Find the critical path (longest dependency chain)."""
        # Build reverse graph
        reverse_graph = {rid: set() for rid in request_ids}
        for rid in request_ids:
            for dep in self._requests[rid].dependencies:
                if dep in reverse_graph:
                    reverse_graph[dep].add(rid)
        
        # Find all paths from roots to leaves
        roots = [rid for rid in request_ids if not self._requests[rid].dependencies]
        
        longest_path = []
        
        def dfs(node: str, path: List[str]):
            nonlocal longest_path
            path = path + [node]
            
            if len(path) > len(longest_path):
                longest_path = path
            
            for next_node in reverse_graph.get(node, []):
                dfs(next_node, path)
        
        for root in roots:
            dfs(root, [])
        
        return longest_path
    
    def _identify_bottlenecks(self, request_ids: List[str]) -> List[str]:
        """Identify potential bottlenecks."""
        bottlenecks = []
        
        # Count how many requests depend on each
        dependency_count = {}
        for rid in request_ids:
            for dep in self._requests[rid].dependencies:
                if dep in request_ids:
                    dependency_count[dep] = dependency_count.get(dep, 0) + 1
        
        # High fan-out = bottleneck
        for rid, count in dependency_count.items():
            if count > len(request_ids) * 0.3:  # Depends on more than 30%
                bottlenecks.append(rid)
        
        return bottlenecks
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            'total_requests': len(self._requests),
            'pending': sum(1 for r in self._requests.values() if r.status == RequestStatus.PENDING),
            'queued': len(self._queue),
            'running': len(self._running),
            'completed': len(self._completed),
            'failed': self._stats['total_failed'],
            'stats': self._stats.copy(),
        }
    
    def _update_stats(self):
        """Update running statistics."""
        if self._execution_times:
            self._stats['avg_execution_time'] = sum(self._execution_times.values()) / len(self._execution_times)
    
    def on_status_change(self, callback: Callable):
        """Set callback for status changes."""
        self._on_status_change = callback
    
    def _notify_status_change(self, req: ScheduledRequest):
        """Notify status change."""
        if self._on_status_change:
            self._on_status_change(req)
    
    def clear_completed(self):
        """Clear completed and failed requests."""
        to_remove = [
            rid for rid, req in self._requests.items()
            if req.status in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED]
        ]
        for rid in to_remove:
            del self._requests[rid]
        
        self._completed.clear()


class AsyncRequestScheduler(RequestScheduler):
    """Async-aware request scheduler with execution capabilities."""
    
    def __init__(self, max_parallel: int = 3, strategy: ScheduleStrategy = ScheduleStrategy.DEPENDENCY):
        super().__init__(max_parallel, strategy)
        self._semaphore = asyncio.Semaphore(max_parallel)
    
    async def execute_next(self) -> Optional[ScheduledRequest]:
        """Execute the next request in queue."""
        req = self.get_next()
        if not req or not req.executor:
            return None
        
        async with self._semaphore:
            self.mark_running(req.request_id)
            
            try:
                if asyncio.iscoroutinefunction(req.executor):
                    result = await req.executor(req)
                else:
                    result = req.executor(req)
                
                self.mark_completed(req.request_id, result)
            except Exception as e:
                self.mark_failed(req.request_id, str(e))
        
        return req
    
    async def execute_all(self) -> Dict[str, Any]:
        """Execute all pending requests."""
        results = {}
        
        while True:
            req = await self.execute_next()
            if not req:
                # Check if anything left
                if not self._queue and not self._running:
                    break
                await asyncio.sleep(0.1)
            else:
                results[req.request_id] = req.result
        
        return results
    
    async def execute_plan(self, plan: SchedulePlan) -> Dict[str, Any]:
        """Execute according to a plan."""
        results = {}
        
        for group in plan.parallel_groups:
            # Execute group in parallel
            tasks = []
            for rid in group:
                req = self._requests.get(rid)
                if req and req.executor:
                    task = self._execute_single(req)
                    tasks.append(task)
            
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for rid, result in zip(group, group_results):
                if isinstance(result, Exception):
                    self.mark_failed(rid, str(result))
                else:
                    self.mark_completed(rid, result)
                    results[rid] = result
        
        return results
    
    async def _execute_single(self, req: ScheduledRequest) -> Any:
        """Execute a single request."""
        async with self._semaphore:
            self.mark_running(req.request_id)
            
            try:
                if asyncio.iscoroutinefunction(req.executor):
                    return await req.executor(req)
                else:
                    return req.executor(req)
            except Exception as e:
                raise e