"""
COL Resonance Module - Temporal Coherence
Cell 0 OS - TPV Architecture

Temporal coherence tracks continuity over time, ensuring the system
maintains a stable temporal context and recognizes patterns in the
temporal dimension. This is the 'when' layer of TPV coherence.
"""

import asyncio
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from collections import deque
from hashlib import sha256
import json


class TemporalPhase(Enum):
    """Temporal phases of interaction coherence."""
    INITIATION = auto()      # First contact / establishing rhythm
    DEVELOPMENT = auto()     # Building temporal patterns
    MAINTENANCE = auto()     # Sustained coherent interaction
    DISSOLUTION = auto()     # Natural winding down
    REACTIVATION = auto()    # Resuming after pause


class RhythmPattern(Enum):
    """Recognizable interaction rhythms."""
    BURST = auto()           # Intense, short engagement
    STEADY = auto()          # Consistent, regular engagement
    INTERMITTENT = auto()    # Sporadic with patterns
    DEEP = auto()            # Long, sustained engagement
    REACTIVE = auto()        # Response-driven, not initiative-driven


@dataclass
class TemporalAnchor:
    """A point in time with semantic significance."""
    anchor_id: str
    timestamp: float
    phase: TemporalPhase
    context_hash: str        # Hash of relevant context
    resonance_signature: float  # TPV coherence at this moment
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def age_seconds(self) -> float:
        """Get age of anchor in seconds."""
        return time.time() - self.timestamp
    
    def decay_factor(self, half_life: float = 3600.0) -> float:
        """Exponential decay factor based on age."""
        return 0.5 ** (self.age_seconds() / half_life)


@dataclass
class TemporalWindow:
    """A bounded temporal context."""
    window_id: str
    start_time: float
    end_time: Optional[float] = None
    anchors: List[TemporalAnchor] = field(default_factory=list)
    coherence_history: deque = field(default_factory=lambda: deque(maxlen=100))
    dominant_rhythm: Optional[RhythmPattern] = None
    
    def duration(self) -> float:
        """Get duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def is_active(self) -> bool:
        """Check if window is still open."""
        return self.end_time is None
    
    def average_coherence(self) -> float:
        """Calculate average coherence in window."""
        if not self.coherence_history:
            return 0.0
        return sum(self.coherence_history) / len(self.coherence_history)


@dataclass
class TemporalSignature:
    """Unique temporal fingerprint of an interaction pattern."""
    signature_id: str
    rhythm_pattern: RhythmPattern
    avg_interval: float
    variance: float
    predictability: float  # 0-1, higher = more predictable
    last_occurrence: float
    occurrence_count: int
    context_similarity: float  # How similar contexts trigger this pattern


class TemporalContinuity:
    """
    Tracks and maintains temporal coherence.
    
    This is the 'when' component of TPV - ensuring that interactions
    maintain temporal continuity, recognizing patterns over time,
    and adapting to the user's temporal rhythm.
    """
    
    def __init__(
        self,
        max_anchors: int = 1000,
        coherence_window: int = 100,
        rhythm_detection_window: int = 10,
    ):
        self.anchors: deque = deque(maxlen=max_anchors)
        self.windows: Dict[str, TemporalWindow] = {}
        self.signatures: Dict[str, TemporalSignature] = {}
        self.current_window: Optional[TemporalWindow] = None
        self.coherence_history: deque = deque(maxlen=coherence_window)
        self.intervals: deque = deque(maxlen=rhythm_detection_window)
        
        self._last_interaction: Optional[float] = None
        self._rhythm: RhythmPattern = RhythmPattern.STEADY
        self._coherence_state: float = 1.0
        self._lock = asyncio.Lock()
    
    async def record_interaction(
        self,
        context: Dict[str, Any],
        phase: TemporalPhase = TemporalPhase.MAINTENANCE,
        resonance: float = 1.0
    ) -> TemporalAnchor:
        """Record a temporal anchor from an interaction."""
        async with self._lock:
            now = time.time()
            
            # Calculate interval and update rhythm detection
            if self._last_interaction is not None:
                interval = now - self._last_interaction
                self.intervals.append(interval)
                self._detect_rhythm()
            
            # Create context hash
            context_str = json.dumps(context, sort_keys=True, default=str)
            context_hash = sha256(context_str.encode()).hexdigest()[:16]
            
            # Create anchor
            anchor = TemporalAnchor(
                anchor_id=f"anchor_{now:.6f}",
                timestamp=now,
                phase=phase,
                context_hash=context_hash,
                resonance_signature=resonance,
                metadata=context
            )
            
            self.anchors.append(anchor)
            self._last_interaction = now
            
            # Update current window
            if self.current_window:
                self.current_window.anchors.append(anchor)
                self.current_window.coherence_history.append(resonance)
            
            # Update coherence state
            await self._update_coherence(resonance)
            
            return anchor
    
    def _detect_rhythm(self) -> None:
        """Detect the current rhythm pattern from intervals."""
        if len(self.intervals) < 3:
            return
        
        intervals = list(self.intervals)
        avg_interval = statistics.mean(intervals)
        variance = statistics.variance(intervals) if len(intervals) > 1 else 0
        
        # Classify rhythm
        if avg_interval < 30:  # Very frequent
            self._rhythm = RhythmPattern.BURST
        elif avg_interval < 300:  # Minutes
            self._rhythm = RhythmPattern.STEADY
        elif variance > avg_interval * 0.5:  # Irregular
            self._rhythm = RhythmPattern.INTERMITTENT
        elif avg_interval > 1800:  # 30+ minutes
            self._rhythm = RhythmPattern.DEEP
        else:
            self._rhythm = RhythmPattern.REACTIVE
    
    async def _update_coherence(self, resonance: float) -> None:
        """Update temporal coherence state."""
        # Exponential moving average
        alpha = 0.3  # Adaptation rate
        self._coherence_state = (
            alpha * resonance + (1 - alpha) * self._coherence_state
        )
        self.coherence_history.append(self._coherence_state)
    
    async def open_window(
        self,
        window_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> TemporalWindow:
        """Open a new temporal window."""
        async with self._lock:
            # Close current window if exists
            if self.current_window and self.current_window.is_active():
                self.current_window.end_time = time.time()
            
            window = TemporalWindow(
                window_id=window_id or f"window_{time.time():.6f}",
                start_time=time.time(),
                metadata=context or {}
            )
            
            self.windows[window.window_id] = window
            self.current_window = window
            
            return window
    
    async def close_window(self, window_id: Optional[str] = None) -> Optional[TemporalWindow]:
        """Close a temporal window."""
        async with self._lock:
            window = None
            if window_id:
                window = self.windows.get(window_id)
            elif self.current_window:
                window = self.current_window
            
            if window and window.is_active():
                window.end_time = time.time()
                # Determine dominant rhythm for window
                window.dominant_rhythm = self._rhythm
            
            if window == self.current_window:
                self.current_window = None
            
            return window
    
    def get_coherence(self) -> float:
        """Get current temporal coherence state."""
        return self._coherence_state
    
    def get_rhythm(self) -> RhythmPattern:
        """Get current detected rhythm."""
        return self._rhythm
    
    def get_continuity_score(self) -> float:
        """
        Calculate temporal continuity score.
        
        Returns 0-1 score representing how continuous the temporal
        context is. Lower if there are gaps or discontinuities.
        """
        if not self.anchors:
            return 0.0
        
        # Recent anchors contribute more
        total_weight = 0.0
        weighted_coherence = 0.0
        
        for anchor in self.anchors:
            weight = anchor.decay_factor(half_life=3600.0)
            total_weight += weight
            weighted_coherence += weight * anchor.resonance_signature
        
        return weighted_coherence / max(total_weight, 0.001)
    
    def predict_next_interaction(self) -> Optional[float]:
        """Predict timestamp of next interaction based on rhythm."""
        if not self.intervals or self._last_interaction is None:
            return None
        
        avg_interval = statistics.mean(self.intervals)
        return self._last_interaction + avg_interval
    
    def find_pattern_matches(
        self,
        context_hash: str,
        min_similarity: float = 0.7
    ) -> List[TemporalAnchor]:
        """Find anchors with similar contexts."""
        matches = []
        for anchor in self.anchors:
            # Simple hash comparison - could use fuzzy matching
            similarity = sum(
                a == b for a, b in zip(anchor.context_hash, context_hash)
            ) / len(context_hash)
            if similarity >= min_similarity:
                matches.append(anchor)
        return matches
    
    def get_temporal_summary(self) -> Dict[str, Any]:
        """Get summary of temporal coherence state."""
        return {
            "coherence": self._coherence_state,
            "rhythm": self._rhythm.name,
            "continuity_score": self.get_continuity_score(),
            "total_anchors": len(self.anchors),
            "active_windows": sum(1 for w in self.windows.values() if w.is_active()),
            "current_phase": self.anchors[-1].phase.name if self.anchors else None,
            "avg_interval_seconds": statistics.mean(self.intervals) if self.intervals else None,
            "predicted_next": self.predict_next_interaction(),
        }
    
    def create_signature(
        self,
        pattern_name: str,
        context_filter: Optional[Callable] = None
    ) -> TemporalSignature:
        """Create a temporal signature from observed patterns."""
        relevant_anchors = [
            a for a in self.anchors
            if context_filter is None or context_filter(a.metadata)
        ]
        
        if len(relevant_anchors) < 2:
            return TemporalSignature(
                signature_id=f"sig_{pattern_name}",
                rhythm_pattern=self._rhythm,
                avg_interval=0.0,
                variance=0.0,
                predictability=0.0,
                last_occurrence=time.time(),
                occurrence_count=len(relevant_anchors),
                context_similarity=0.0
            )
        
        # Calculate intervals
        timestamps = sorted([a.timestamp for a in relevant_anchors])
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        
        avg_interval = statistics.mean(intervals)
        variance = statistics.variance(intervals) if len(intervals) > 1 else 0
        
        # Predictability: lower variance = higher predictability
        if avg_interval > 0:
            cv = variance / avg_interval  # Coefficient of variation
            predictability = max(0.0, 1.0 - cv)
        else:
            predictability = 0.0
        
        sig = TemporalSignature(
            signature_id=f"sig_{pattern_name}_{time.time():.6f}",
            rhythm_pattern=self._rhythm,
            avg_interval=avg_interval,
            variance=variance,
            predictability=predictability,
            last_occurrence=timestamps[-1],
            occurrence_count=len(relevant_anchors),
            context_similarity=1.0  # Would calculate from actual contexts
        )
        
        self.signatures[sig.signature_id] = sig
        return sig


import statistics  # Import moved to top for module clarity
