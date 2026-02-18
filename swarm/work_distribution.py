"""
Cell 0 OS - Work Distribution
Intelligent task distribution and load balancing for 200+ agents.
"""

import asyncio
import hashlib
import heapq
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import random


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskState(Enum):
    """Task lifecycle states."""
    PENDING = auto()
    ASSIGNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    RETRYING = auto()


@dataclass
class TaskRequirements:
    """Task resource and capability requirements."""
    capabilities: List[str] = field(default_factory=list)
    min_memory_mb: float = 0
    min_cpu_cores: float = 0
    min_gpu_memory_mb: float = 0
    estimated_duration_sec: float = 60.0
    dependencies: List[str] = field(default_factory=list)
    exclusive_agent: bool = False


@dataclass
class Task:
    """Complete task descriptor."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority
    requirements: TaskRequirements
    
    # State
    state: TaskState = TaskState.PENDING
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Execution
    attempts: int = 0
    max_attempts: int = 3
    result: Any = None
    error: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkUnit:
    """Unit of work assigned to agent."""
    unit_id: str
    task_id: str
    payload: Dict[str, Any]
    deadline: Optional[float] = None
    checkpoint_interval: float = 30.0


@dataclass
class AgentLoad:
    """Current load metrics for an agent."""
    agent_id: str
    active_tasks: int = 0
    queued_tasks: int = 0
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    gpu_utilization: float = 0.0
    network_io_mbps: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    agent_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_sec: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)


class TaskQueue:
    """
    Priority queue for task management.
    
    Supports:
    - Multiple priority levels
    - Fair scheduling within priorities
    - Task dependencies
    - Deadline awareness
    """
    
    def __init__(self):
        self.queues: Dict[TaskPriority, List[Task]] = {
            p: [] for p in TaskPriority
        }
        self.task_map: Dict[str, Task] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.completed_dependencies: Set[str] = set()
        self.lock = asyncio.Lock()
        
    async def enqueue(self, task: Task) -> bool:
        """Add task to queue."""
        async with self.lock:
            if task.task_id in self.task_map:
                return False
                
            self.task_map[task.task_id] = task
            
            # Build dependency graph
            for dep in task.requirements.dependencies:
                self.dependency_graph[task.task_id].add(dep)
            
            # Check if ready (no pending dependencies)
            if self._is_ready(task):
                task.state = TaskState.PENDING
                self.queues[task.priority].append(task)
                self._maintain_priority_order(task.priority)
            else:
                # Wait for dependencies
                task.state = TaskState.PENDING
                
            return True
            
    async def dequeue(self, agent_capabilities: List[str],
                     agent_resources: Dict[str, float]) -> Optional[Task]:
        """Get next suitable task for agent."""
        async with self.lock:
            # Check from highest to lowest priority
            for priority in TaskPriority:
                queue = self.queues[priority]
                
                for i, task in enumerate(queue):
                    if task.state != TaskState.PENDING:
                        continue
                        
                    # Check dependencies
                    if not self._is_ready(task):
                        continue
                        
                    # Check capabilities
                    if not self._matches_capabilities(task, agent_capabilities):
                        continue
                        
                    # Check resources
                    if not self._has_resources(task, agent_resources):
                        continue
                    
                    # Found suitable task
                    task.state = TaskState.ASSIGNED
                    queue.pop(i)
                    return task
                    
            return None
            
    async def complete_task(self, task_id: str, result: TaskResult):
        """Mark task as completed."""
        async with self.lock:
            if task_id not in self.task_map:
                return False
                
            task = self.task_map[task_id]
            task.state = TaskState.COMPLETED if result.success else TaskState.FAILED
            task.result = result.result
            task.error = result.error
            task.completed_at = time.time()
            
            self.completed_dependencies.add(task_id)
            
            # Check for newly ready tasks
            await self._promote_ready_tasks()
            
            return True
            
    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        async with self.lock:
            if task_id not in self.task_map:
                return False
                
            task = self.task_map[task_id]
            if task.attempts >= task.max_attempts:
                return False
                
            task.attempts += 1
            task.state = TaskState.PENDING
            task.assigned_agent = None
            
            self.queues[task.priority].append(task)
            self._maintain_priority_order(task.priority)
            
            return True
            
    def _is_ready(self, task: Task) -> bool:
        """Check if task dependencies are satisfied."""
        deps = self.dependency_graph.get(task.task_id, set())
        return deps.issubset(self.completed_dependencies)
        
    def _matches_capabilities(self, task: Task, capabilities: List[str]) -> bool:
        """Check if agent has required capabilities."""
        required = set(task.requirements.capabilities)
        available = set(capabilities)
        return required.issubset(available)
        
    def _has_resources(self, task: Task, resources: Dict[str, float]) -> bool:
        """Check if agent has required resources."""
        req = task.requirements
        
        if req.min_memory_mb > resources.get("memory_mb", 0):
            return False
        if req.min_cpu_cores > resources.get("cpu_cores", 0):
            return False
        if req.min_gpu_memory_mb > resources.get("gpu_memory_mb", 0):
            return False
            
        return True
        
    def _maintain_priority_order(self, priority: TaskPriority):
        """Keep queue sorted by creation time (FIFO within priority)."""
        self.queues[priority].sort(key=lambda t: t.created_at)
        
    async def _promote_ready_tasks(self):
        """Promote tasks whose dependencies are now satisfied."""
        for task in list(self.task_map.values()):
            if task.state == TaskState.PENDING and self._is_ready(task):
                # Already in queue or needs to be added
                if task not in self.queues[task.priority]:
                    self.queues[task.priority].append(task)
                    self._maintain_priority_order(task.priority)
                    
    def get_stats(self) -> Dict:
        """Get queue statistics."""
        return {
            "total_tasks": len(self.task_map),
            "pending": sum(1 for t in self.task_map.values() if t.state == TaskState.PENDING),
            "running": sum(1 for t in self.task_map.values() if t.state == TaskState.RUNNING),
            "completed": sum(1 for t in self.task_map.values() if t.state == TaskState.COMPLETED),
            "failed": sum(1 for t in self.task_map.values() if t.state == TaskState.FAILED),
            "by_priority": {
                p.name: len(self.queues[p]) for p in TaskPriority
            }
        }


class LoadBalancer:
    """
    Intelligent load balancing for agent swarm.
    
    Algorithms:
    - Round-robin: Fair distribution
    - Least-loaded: Minimize queue depth
    - Weighted: Account for agent capacity
    - Capability-aware: Match skills to tasks
    - Predictive: Anticipate load patterns
    """
    
    def __init__(self):
        self.agent_loads: Dict[str, AgentLoad] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.agent_weights: Dict[str, float] = {}
        self.round_robin_index = 0
        self.history: List[Dict] = []
        self.lock = asyncio.Lock()
        
    def update_agent_load(self, agent_id: str, load: AgentLoad):
        """Update agent load metrics."""
        self.agent_loads[agent_id] = load
        
    def update_agent_capabilities(self, agent_id: str, capabilities: List[str]):
        """Update agent capabilities."""
        self.agent_capabilities[agent_id] = capabilities
        
    def set_agent_weight(self, agent_id: str, weight: float):
        """Set agent weight for weighted balancing."""
        self.agent_weights[agent_id] = weight
        
    async def select_agent(self, task: Task,
                          available_agents: List[str],
                          algorithm: str = "adaptive") -> Optional[str]:
        """Select best agent for task."""
        async with self.lock:
            # Filter agents by capability
            capable_agents = [
                aid for aid in available_agents
                if self._has_capabilities(aid, task.requirements.capabilities)
            ]
            
            if not capable_agents:
                return None
                
            # Apply selection algorithm
            if algorithm == "round_robin":
                return self._round_robin(capable_agents)
            elif algorithm == "least_loaded":
                return self._least_loaded(capable_agents)
            elif algorithm == "weighted":
                return self._weighted(capable_agents)
            elif algorithm == "capacity":
                return self._capacity_based(capable_agents, task)
            else:  # adaptive
                return self._adaptive(capable_agents, task)
                
    def _has_capabilities(self, agent_id: str, required: List[str]) -> bool:
        """Check if agent has required capabilities."""
        if not required:
            return True
        available = set(self.agent_capabilities.get(agent_id, []))
        return set(required).issubset(available)
        
    def _round_robin(self, agents: List[str]) -> str:
        """Round-robin selection."""
        if not agents:
            return None
            
        idx = self.round_robin_index % len(agents)
        self.round_robin_index += 1
        return agents[idx]
        
    def _least_loaded(self, agents: List[str]) -> str:
        """Select least loaded agent."""
        if not agents:
            return None
            
        def get_load(agent_id):
            load = self.agent_loads.get(agent_id)
            if not load:
                return 0
            return load.active_tasks + load.queued_tasks
            
        return min(agents, key=get_load)
        
    def _weighted(self, agents: List[str]) -> str:
        """Weighted random selection."""
        if not agents:
            return None
            
        weights = [self.agent_weights.get(aid, 1.0) for aid in agents]
        total = sum(weights)
        
        r = random.uniform(0, total)
        cumulative = 0
        
        for agent_id, weight in zip(agents, weights):
            cumulative += weight
            if r <= cumulative:
                return agent_id
                
        return agents[-1]
        
    def _capacity_based(self, agents: List[str], task: Task) -> str:
        """Select based on available capacity."""
        if not agents:
            return None
            
        scores = []
        for agent_id in agents:
            load = self.agent_loads.get(agent_id)
            if not load:
                scores.append((agent_id, 1.0))
                continue
                
            # Calculate capacity score
            cpu_available = 1.0 - load.cpu_utilization
            mem_available = 1.0 - load.memory_utilization
            
            score = (cpu_available + mem_available) / 2.0
            score /= (1 + load.active_tasks)  # Penalty for active tasks
            
            scores.append((agent_id, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]
        
    def _adaptive(self, agents: List[str], task: Task) -> str:
        """
        Adaptive selection combining multiple factors.
        
        Factors:
        - Current load
        - Task completion history
        - Network proximity
        - Specialization match
        """
        if not agents:
            return None
            
        scores = []
        for agent_id in agents:
            score = 0.0
            
            # Load factor (0-40 points)
            load = self.agent_loads.get(agent_id)
            if load:
                load_score = 40 * (1.0 - (load.active_tasks / 10.0))
                score += max(0, load_score)
            else:
                score += 40
                
            # Weight factor (0-20 points)
            weight = self.agent_weights.get(agent_id, 1.0)
            score += 20 * weight
            
            # Recency factor - prefer recently active agents (0-10 points)
            if load:
                recency = max(0, 10 - (time.time() - load.last_updated))
                score += recency
                
            scores.append((agent_id, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]


class WorkDistributor:
    """
    High-level work distribution coordinator.
    
    Orchestrates task queue, load balancing, and agent assignment.
    """
    
    def __init__(self, coordinator_id: str):
        self.coordinator_id = coordinator_id
        self.task_queue = TaskQueue()
        self.load_balancer = LoadBalancer()
        
        # Agent management
        self.agent_assignments: Dict[str, Set[str]] = defaultdict(set)
        self.agent_callbacks: Dict[str, Callable[[WorkUnit], None]] = {}
        
        # Task tracking
        self.task_results: Dict[str, TaskResult] = {}
        self.result_callbacks: Dict[str, List[Callable[[TaskResult], None]]] = defaultdict(list)
        
        # Configuration
        self.rebalance_interval = 30.0
        self.max_task_duration = 3600.0
        
        # Running state
        self.running = False
        
    async def start(self):
        """Start work distribution."""
        self.running = True
        asyncio.create_task(self._assignment_loop())
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._rebalancing_loop())
        
    async def stop(self):
        """Stop work distribution."""
        self.running = False
        
    def register_agent(self, agent_id: str, 
                      capabilities: List[str],
                      callback: Callable[[WorkUnit], None]):
        """Register agent for work."""
        self.agent_callbacks[agent_id] = callback
        self.load_balancer.update_agent_capabilities(agent_id, capabilities)
        
    def unregister_agent(self, agent_id: str):
        """Unregister agent."""
        self.agent_callbacks.pop(agent_id, None)
        
        # Reassign tasks
        assigned = list(self.agent_assignments.get(agent_id, []))
        for task_id in assigned:
            asyncio.create_task(self._reassign_task(task_id))
            
    def update_agent_load(self, agent_id: str, load: AgentLoad):
        """Update agent load information."""
        self.load_balancer.update_agent_load(agent_id, load)
        
    async def submit_task(self, task_type: str,
                         payload: Dict[str, Any],
                         priority: TaskPriority = TaskPriority.NORMAL,
                         requirements: Optional[TaskRequirements] = None,
                         tags: Optional[List[str]] = None) -> str:
        """Submit a new task."""
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            requirements=requirements or TaskRequirements(),
            tags=tags or []
        )
        
        await self.task_queue.enqueue(task)
        
        return task_id
        
    async def submit_batch(self, tasks: List[Tuple[str, Dict, TaskPriority]]) -> List[str]:
        """Submit multiple tasks."""
        task_ids = []
        for task_type, payload, priority in tasks:
            task_id = await self.submit_task(task_type, payload, priority)
            task_ids.append(task_id)
        return task_ids
        
    async def on_task_result(self, result: TaskResult):
        """Handle task completion."""
        # Update task queue
        await self.task_queue.complete_task(result.task_id, result)
        
        # Store result
        self.task_results[result.task_id] = result
        
        # Clear assignment
        for agent_id, tasks in self.agent_assignments.items():
            tasks.discard(result.task_id)
            
        # Notify callbacks
        for callback in self.result_callbacks.get(result.task_id, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(result))
                else:
                    callback(result)
            except Exception:
                pass
                
        # Retry if failed
        if not result.success:
            task = self.task_queue.task_map.get(result.task_id)
            if task and task.attempts < task.max_attempts:
                await self.task_queue.retry_task(result.task_id)
                
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result."""
        return self.task_results.get(task_id)
        
    def wait_for_result(self, task_id: str, timeout: float = 60.0) -> Optional[TaskResult]:
        """Wait for task completion."""
        # This would use futures in practice
        return self.task_results.get(task_id)
        
    async def _assignment_loop(self):
        """Main task assignment loop."""
        while self.running:
            await asyncio.sleep(0.1)  # 100ms assignment interval
            
            # Get available agents
            available = [
                aid for aid in self.agent_callbacks.keys()
                if aid in self.load_balancer.agent_loads
            ]
            
            if not available:
                continue
                
            # Get agent capabilities
            agent_caps = {
                aid: self.load_balancer.agent_capabilities.get(aid, [])
                for aid in available
            }
            
            # Get agent resources
            agent_resources = {
                aid: {
                    "memory_mb": 1000,  # Would come from actual metrics
                    "cpu_cores": 4,
                    "gpu_memory_mb": 0
                }
                for aid in available
            }
            
            # Try to assign tasks
            for agent_id in available:
                task = await self.task_queue.dequeue(
                    agent_caps.get(agent_id, []),
                    agent_resources.get(agent_id, {})
                )
                
                if task:
                    await self._assign_task(agent_id, task)
                    
    async def _assign_task(self, agent_id: str, task: Task):
        """Assign task to agent."""
        work_unit = WorkUnit(
            unit_id=str(uuid.uuid4()),
            task_id=task.task_id,
            payload=task.payload,
            deadline=time.time() + self.max_task_duration
        )
        
        task.state = TaskState.RUNNING
        task.assigned_agent = agent_id
        task.started_at = time.time()
        task.attempts += 1
        
        self.agent_assignments[agent_id].add(task.task_id)
        
        # Send to agent
        callback = self.agent_callbacks.get(agent_id)
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(work_unit))
                else:
                    callback(work_unit)
            except Exception as e:
                # Assignment failed
                task.state = TaskState.FAILED
                task.error = str(e)
                await self.task_queue.complete_task(
                    task.task_id,
                    TaskResult(task_id=task.task_id, agent_id=agent_id, success=False, error=str(e))
                )
                
    async def _reassign_task(self, task_id: str):
        """Reassign task after agent failure."""
        task = self.task_queue.task_map.get(task_id)
        if not task:
            return
            
        # Reset task state
        task.state = TaskState.PENDING
        task.assigned_agent = None
        
        # Re-enqueue
        await self.task_queue.enqueue(task)
        
    async def _monitoring_loop(self):
        """Monitor task execution."""
        while self.running:
            await asyncio.sleep(10.0)
            
            now = time.time()
            
            # Check for stuck tasks
            for task in list(self.task_queue.task_map.values()):
                if task.state == TaskState.RUNNING:
                    if task.started_at and (now - task.started_at) > self.max_task_duration:
                        # Task stuck, mark as failed
                        await self.on_task_result(TaskResult(
                            task_id=task.task_id,
                            agent_id=task.assigned_agent or "unknown",
                            success=False,
                            error="Task timeout"
                        ))
                        
    async def _rebalancing_loop(self):
        """Periodic load rebalancing."""
        while self.running:
            await asyncio.sleep(self.rebalance_interval)
            
            # Analyze load distribution
            loads = [
                (aid, load.active_tasks + load.queued_tasks)
                for aid, load in self.load_balancer.agent_loads.items()
            ]
            
            if not loads:
                continue
                
            loads.sort(key=lambda x: x[1])
            
            # Check for imbalance
            if loads[-1][1] - loads[0][1] > 5:
                # Migrate tasks from heavily loaded to lightly loaded
                # Implementation would move queued tasks
                pass
                
    def get_stats(self) -> Dict:
        """Get distribution statistics."""
        return {
            "task_queue": self.task_queue.get_stats(),
            "active_agents": len(self.agent_callbacks),
            "agent_assignments": {
                aid: len(tasks) for aid, tasks in self.agent_assignments.items()
            },
            "completed_tasks": len(self.task_results)
        }
