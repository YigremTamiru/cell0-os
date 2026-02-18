"""
COL-Flow Pressure Module
Cell 0 OS - Cognitive Operating Layer

Context pressure detection and management.
Monitors conversation state and triggers actions when approaching limits.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Callable, Tuple
from collections import deque


class PressureLevel(Enum):
    """Levels of context pressure."""
    NORMAL = auto()       # Operating normally
    ELEVATED = auto()     # Approaching soft limits
    HIGH = auto()         # Near hard limits
    CRITICAL = auto()     # At or exceeding limits


class PressureDimension(Enum):
    """Dimensions of pressure."""
    TOKEN_COUNT = auto()       # Total tokens
    TURN_COUNT = auto()        # Number of turns
    TIME_ELAPSED = auto()      # Time since start
    COMPLEXITY = auto()        # Complexity score
    ATTENTION_SPAN = auto()    # Focus duration
    TOPIC_DRIFT = auto()       # How far from original topic


@dataclass
class PressureReading:
    """A reading of context pressure."""
    dimension: PressureDimension
    current: float
    soft_limit: float
    hard_limit: float
    ratio: float  # current / hard_limit
    timestamp: float = field(default_factory=time.time)


@dataclass
class PressureSnapshot:
    """Complete pressure snapshot across all dimensions."""
    overall_level: PressureLevel
    readings: Dict[PressureDimension, PressureReading]
    overall_ratio: float
    timestamp: float = field(default_factory=time.time)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ConversationSummary:
    """Summary of conversation for context reduction."""
    key_points: List[str]
    decisions_made: List[str]
    action_items: List[str]
    open_questions: List[str]
    topics_covered: List[str]
    token_savings: int
    original_turns: int
    summary_turn: int


class PressureManager:
    """
    Manages context pressure across multiple dimensions.
    
    Monitors:
    - Token usage
    - Turn count
    - Time elapsed
    - Conversation complexity
    - Topic drift
    
    Actions:
    - Warn when approaching limits
    - Trigger summarization
    - Suggest context reduction
    - Recommend conversation restart
    """
    
    # Default limits
    DEFAULT_SOFT_TOKEN_LIMIT = 6000
    DEFAULT_HARD_TOKEN_LIMIT = 8000
    DEFAULT_SOFT_TURN_LIMIT = 50
    DEFAULT_HARD_TURN_LIMIT = 100
    DEFAULT_SOFT_TIME_LIMIT = 1800  # 30 minutes
    DEFAULT_HARD_TIME_LIMIT = 3600  # 60 minutes
    
    def __init__(
        self,
        soft_token_limit: int = DEFAULT_SOFT_TOKEN_LIMIT,
        hard_token_limit: int = DEFAULT_HARD_TOKEN_LIMIT,
        soft_turn_limit: int = DEFAULT_SOFT_TURN_LIMIT,
        hard_turn_limit: int = DEFAULT_HARD_TURN_LIMIT,
        soft_time_limit: int = DEFAULT_SOFT_TIME_LIMIT,
        hard_time_limit: int = DEFAULT_HARD_TIME_LIMIT,
    ):
        """
        Initialize pressure manager.
        
        Args:
            soft_token_limit: Warning threshold for tokens
            hard_token_limit: Maximum tokens before forced action
            soft_turn_limit: Warning threshold for turns
            hard_turn_limit: Maximum turns before forced action
            soft_time_limit: Warning threshold for time (seconds)
            hard_time_limit: Maximum time before forced action
        """
        self.limits = {
            PressureDimension.TOKEN_COUNT: (soft_token_limit, hard_token_limit),
            PressureDimension.TURN_COUNT: (soft_turn_limit, hard_turn_limit),
            PressureDimension.TIME_ELAPSED: (soft_time_limit, hard_time_limit),
            PressureDimension.COMPLEXITY: (0.7, 0.9),
            PressureDimension.ATTENTION_SPAN: (600, 1200),  # 10-20 minutes
            PressureDimension.TOPIC_DRIFT: (0.5, 0.8),
        }
        
        # State tracking
        self._current_tokens = 0
        self._turn_count = 0
        self._start_time = time.time()
        self._last_interaction = time.time()
        self._topic_history: deque = deque(maxlen=10)
        self._complexity_score = 0.0
        
        # History
        self._pressure_history: deque = deque(maxlen=100)
        self._summaries: List[ConversationSummary] = []
        
        # Callbacks
        self._on_pressure_change: Optional[Callable] = None
        self._on_summarize: Optional[Callable] = None
        self._last_level = PressureLevel.NORMAL
    
    def update_tokens(self, count: int):
        """Update current token count."""
        self._current_tokens = count
    
    def increment_turn(self):
        """Increment turn counter."""
        self._turn_count += 1
        self._last_interaction = time.time()
    
    def add_topic(self, topic: str):
        """Add a topic to track drift."""
        self._topic_history.append(topic)
    
    def set_complexity(self, score: float):
        """Set conversation complexity score (0-1)."""
        self._complexity_score = max(0.0, min(1.0, score))
    
    def check_pressure(self) -> PressureSnapshot:
        """
        Check current pressure across all dimensions.
        
        Returns:
            PressureSnapshot with current state
        """
        readings = {}
        
        # Token count
        readings[PressureDimension.TOKEN_COUNT] = self._check_dimension(
            PressureDimension.TOKEN_COUNT,
            self._current_tokens
        )
        
        # Turn count
        readings[PressureDimension.TURN_COUNT] = self._check_dimension(
            PressureDimension.TURN_COUNT,
            self._turn_count
        )
        
        # Time elapsed
        elapsed = time.time() - self._start_time
        readings[PressureDimension.TIME_ELAPSED] = self._check_dimension(
            PressureDimension.TIME_ELAPSED,
            elapsed
        )
        
        # Attention span (time since last interaction)
        attention = time.time() - self._last_interaction
        readings[PressureDimension.ATTENTION_SPAN] = PressureReading(
            dimension=PressureDimension.ATTENTION_SPAN,
            current=attention,
            soft_limit=self.limits[PressureDimension.ATTENTION_SPAN][0],
            hard_limit=self.limits[PressureDimension.ATTENTION_SPAN][1],
            ratio=attention / self.limits[PressureDimension.ATTENTION_SPAN][1]
        )
        
        # Complexity
        readings[PressureDimension.COMPLEXITY] = self._check_dimension(
            PressureDimension.COMPLEXITY,
            self._complexity_score
        )
        
        # Topic drift
        drift = self._calculate_topic_drift()
        readings[PressureDimension.TOPIC_DRIFT] = self._check_dimension(
            PressureDimension.TOPIC_DRIFT,
            drift
        )
        
        # Determine overall level
        max_ratio = max(r.ratio for r in readings.values())
        overall_level = self._ratio_to_level(max_ratio)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(readings, overall_level)
        
        snapshot = PressureSnapshot(
            overall_level=overall_level,
            readings=readings,
            overall_ratio=max_ratio,
            recommendations=recommendations
        )
        
        self._pressure_history.append(snapshot)
        
        # Notify if level changed
        if overall_level != self._last_level:
            self._last_level = overall_level
            if self._on_pressure_change:
                self._on_pressure_change(snapshot)
        
        return snapshot
    
    def _check_dimension(self, dimension: PressureDimension, current: float) -> PressureReading:
        """Check pressure for a single dimension."""
        soft, hard = self.limits[dimension]
        ratio = current / hard if hard > 0 else 0
        
        return PressureReading(
            dimension=dimension,
            current=current,
            soft_limit=soft,
            hard_limit=hard,
            ratio=ratio
        )
    
    def _calculate_topic_drift(self) -> float:
        """Calculate how far conversation has drifted from original topic."""
        if len(self._topic_history) < 2:
            return 0.0
        
        # Simple heuristic: number of unique topics relative to history size
        unique_topics = len(set(self._topic_history))
        return unique_topics / len(self._topic_history)
    
    def _ratio_to_level(self, ratio: float) -> PressureLevel:
        """Convert pressure ratio to level."""
        if ratio >= 1.0:
            return PressureLevel.CRITICAL
        elif ratio >= 0.85:
            return PressureLevel.HIGH
        elif ratio >= 0.7:
            return PressureLevel.ELEVATED
        else:
            return PressureLevel.NORMAL
    
    def _generate_recommendations(
        self,
        readings: Dict[PressureDimension, PressureReading],
        level: PressureLevel
    ) -> List[str]:
        """Generate recommendations based on pressure."""
        recommendations = []
        
        if level == PressureLevel.NORMAL:
            return recommendations
        
        # Check specific dimensions
        if readings[PressureDimension.TOKEN_COUNT].ratio > 0.7:
            recommendations.append("Consider summarizing conversation to reduce token usage")
        
        if readings[PressureDimension.TURN_COUNT].ratio > 0.7:
            recommendations.append("Many turns in this conversation - consider starting fresh")
        
        if readings[PressureDimension.TIME_ELAPSED].ratio > 0.7:
            recommendations.append("Long conversation - may want to wrap up or summarize")
        
        if readings[PressureDimension.COMPLEXITY].ratio > 0.7:
            recommendations.append("High complexity - consider breaking into simpler requests")
        
        if readings[PressureDimension.TOPIC_DRIFT].ratio > 0.5:
            recommendations.append("Topic drift detected - refocus on main subject")
        
        if level == PressureLevel.CRITICAL:
            recommendations.append("CRITICAL: Immediate action required - summarizing now")
        
        return recommendations
    
    def should_summarize(self) -> bool:
        """Check if conversation should be summarized."""
        snapshot = self.check_pressure()
        return snapshot.overall_level in [PressureLevel.HIGH, PressureLevel.CRITICAL]
    
    def create_summary(
        self,
        key_points: List[str],
        decisions_made: Optional[List[str]] = None,
        action_items: Optional[List[str]] = None,
        open_questions: Optional[List[str]] = None,
        topics_covered: Optional[List[str]] = None,
        token_savings: int = 0
    ) -> ConversationSummary:
        """
        Create a conversation summary.
        
        Args:
            key_points: Key points from conversation
            decisions_made: Decisions that were made
            action_items: Action items to remember
            open_questions: Unresolved questions
            topics_covered: Topics discussed
            token_savings: Estimated tokens saved
            
        Returns:
            ConversationSummary
        """
        summary = ConversationSummary(
            key_points=key_points,
            decisions_made=decisions_made or [],
            action_items=action_items or [],
            open_questions=open_questions or [],
            topics_covered=topics_covered or list(self._topic_history),
            token_savings=token_savings,
            original_turns=self._turn_count,
            summary_turn=self._turn_count
        )
        
        self._summaries.append(summary)
        
        # Reset counters after summary
        self._current_tokens = 0  # Will be set to summary size
        self._topic_history.clear()
        
        return summary
    
    def get_pressure_trend(self, window: int = 10) -> Tuple[float, str]:
        """
        Get pressure trend over recent history.
        
        Args:
            window: Number of recent readings to consider
            
        Returns:
            (trend_value, description)
        """
        if len(self._pressure_history) < 2:
            return (0.0, "insufficient data")
        
        recent = list(self._pressure_history)[-window:]
        ratios = [s.overall_ratio for s in recent]
        
        if len(ratios) < 2:
            return (0.0, "stable")
        
        # Calculate trend (simple linear regression)
        n = len(ratios)
        x_avg = sum(range(n)) / n
        y_avg = sum(ratios) / n
        
        numerator = sum((i - x_avg) * (y - y_avg) for i, y in enumerate(ratios))
        denominator = sum((i - x_avg) ** 2 for i in range(n))
        
        if denominator == 0:
            return (0.0, "stable")
        
        slope = numerator / denominator
        
        if slope > 0.05:
            return (slope, "increasing")
        elif slope < -0.05:
            return (slope, "decreasing")
        else:
            return (slope, "stable")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pressure management statistics."""
        return {
            'current_tokens': self._current_tokens,
            'turn_count': self._turn_count,
            'time_elapsed': time.time() - self._start_time,
            'topic_count': len(set(self._topic_history)),
            'complexity': self._complexity_score,
            'summaries_created': len(self._summaries),
            'total_token_savings': sum(s.token_savings for s in self._summaries),
        }
    
    def on_pressure_change(self, callback: Callable):
        """Set callback for pressure level changes."""
        self._on_pressure_change = callback
    
    def on_summarize(self, callback: Callable):
        """Set callback for summarization."""
        self._on_summarize = callback
    
    def reset(self, preserve_summaries: bool = True):
        """Reset pressure state."""
        self._current_tokens = 0
        self._turn_count = 0
        self._start_time = time.time()
        self._last_interaction = time.time()
        self._topic_history.clear()
        self._complexity_score = 0.0
        self._pressure_history.clear()
        self._last_level = PressureLevel.NORMAL
        
        if not preserve_summaries:
            self._summaries.clear()


class AdaptivePressureManager(PressureManager):
    """Pressure manager that adapts limits based on usage patterns."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._usage_history: deque = deque(maxlen=50)
        self._adaptation_enabled = True
    
    def record_usage(self, tokens_used: int, duration: float):
        """Record actual usage for adaptation."""
        self._usage_history.append({
            'tokens': tokens_used,
            'duration': duration,
            'timestamp': time.time()
        })
    
    def adapt_limits(self):
        """Adapt limits based on observed patterns."""
        if not self._adaptation_enabled or len(self._usage_history) < 10:
            return
        
        # Calculate averages
        avg_tokens = sum(u['tokens'] for u in self._usage_history) / len(self._usage_history)
        avg_duration = sum(u['duration'] for u in self._usage_history) / len(self._usage_history)
        
        # Adjust soft limits based on patterns
        # If consistently using more, raise limits
        # If consistently using less, lower limits for earlier warnings
        
        token_soft, token_hard = self.limits[PressureDimension.TOKEN_COUNT]
        if avg_tokens > token_soft * 0.8:
            # Running hot, increase limits slightly
            new_soft = int(token_soft * 1.1)
            new_hard = int(token_hard * 1.1)
            self.limits[PressureDimension.TOKEN_COUNT] = (new_soft, new_hard)
        elif avg_tokens < token_soft * 0.3:
            # Running cool, can be more aggressive with warnings
            new_soft = int(token_soft * 0.9)
            self.limits[PressureDimension.TOKEN_COUNT] = (new_soft, token_hard)
    
    def check_pressure(self) -> PressureSnapshot:
        """Check pressure with periodic adaptation."""
        # Adapt every 20 checks
        if len(self._pressure_history) % 20 == 0:
            self.adapt_limits()
        
        return super().check_pressure()