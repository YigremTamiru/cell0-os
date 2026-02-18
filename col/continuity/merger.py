"""
COL-Continuity Conflict Resolution & Merger

Handles merge conflicts when multiple sessions have diverged.
Implements multiple merge strategies for different conflict types.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ConflictType(Enum):
    """Types of merge conflicts."""
    KEY_ADDED_BOTH = "key_added_both"       # Same key added in both branches
    KEY_MODIFIED_BOTH = "key_modified_both"  # Same key modified in both branches
    KEY_DELETED_MODIFIED = "key_deleted_modified"  # Deleted in one, modified in other
    TYPE_MISMATCH = "type_mismatch"          # Same key, different types
    LIST_ORDER = "list_order"                # Conflicting list order changes
    NESTED_CONFLICT = "nested_conflict"      # Conflict within nested structure


class MergeStrategy(Enum):
    """Strategies for resolving conflicts."""
    MANUAL = "manual"               # Require manual resolution
    SOURCE_WINS = "source_wins"     # Source branch takes precedence
    TARGET_WINS = "target_wins"     # Target branch takes precedence
    TIMESTAMP = "timestamp"         # Most recent change wins
    UNION = "union"                 # Combine both values
    INTERSECTION = "intersection"   # Keep only common elements
    CUSTOM = "custom"               # Use custom resolver


@dataclass
class Conflict:
    """Represents a merge conflict."""
    key: str
    conflict_type: ConflictType
    source_value: Any
    target_value: Any
    base_value: Optional[Any] = None
    source_timestamp: Optional[float] = None
    target_timestamp: Optional[float] = None
    resolution: Optional[Any] = None
    strategy_used: Optional[MergeStrategy] = None
    description: str = ""


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    merged_state: dict[str, Any]
    conflicts: list[Conflict] = field(default_factory=list)
    resolved_conflicts: list[Conflict] = field(default_factory=list)
    unresolved_conflicts: list[Conflict] = field(default_factory=list)
    merge_strategy: MergeStrategy = MergeStrategy.TIMESTAMP
    merge_timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_conflicts(self) -> bool:
        """Check if there are unresolved conflicts."""
        return len(self.unresolved_conflicts) > 0


class ConflictResolver:
    """
    Resolves conflicts between divergent states.
    
    Supports multiple resolution strategies and custom resolvers.
    """
    
    def __init__(self):
        self._custom_resolvers: dict[str, Callable[[Conflict], Any]] = {}
        self._strategy_priorities: dict[ConflictType, MergeStrategy] = {
            ConflictType.KEY_ADDED_BOTH: MergeStrategy.TIMESTAMP,
            ConflictType.KEY_MODIFIED_BOTH: MergeStrategy.TIMESTAMP,
            ConflictType.KEY_DELETED_MODIFIED: MergeStrategy.MANUAL,
            ConflictType.TYPE_MISMATCH: MergeStrategy.TARGET_WINS,
            ConflictType.LIST_ORDER: MergeStrategy.UNION,
            ConflictType.NESTED_CONFLICT: MergeStrategy.TIMESTAMP,
        }
    
    def set_strategy_for_type(
        self,
        conflict_type: ConflictType,
        strategy: MergeStrategy,
    ) -> None:
        """Set default strategy for a conflict type."""
        self._strategy_priorities[conflict_type] = strategy
    
    def register_custom_resolver(
        self,
        key_pattern: str,
        resolver: Callable[[Conflict], Any],
    ) -> None:
        """Register a custom resolver for keys matching a pattern."""
        self._custom_resolvers[key_pattern] = resolver
    
    def resolve(
        self,
        conflict: Conflict,
        strategy: Optional[MergeStrategy] = None,
    ) -> Any:
        """
        Resolve a single conflict.
        
        Args:
            conflict: The conflict to resolve
            strategy: Override strategy to use
        
        Returns:
            Resolved value
        """
        if strategy is None:
            strategy = self._strategy_priorities.get(
                conflict.conflict_type,
                MergeStrategy.TIMESTAMP,
            )
        
        # Check for custom resolver
        for pattern, resolver in self._custom_resolvers.items():
            if pattern in conflict.key:
                conflict.strategy_used = MergeStrategy.CUSTOM
                return resolver(conflict)
        
        conflict.strategy_used = strategy
        
        if strategy == MergeStrategy.SOURCE_WINS:
            return conflict.source_value
        
        elif strategy == MergeStrategy.TARGET_WINS:
            return conflict.target_value
        
        elif strategy == MergeStrategy.TIMESTAMP:
            # Compare timestamps if available
            if conflict.source_timestamp and conflict.target_timestamp:
                if conflict.source_timestamp >= conflict.target_timestamp:
                    return conflict.source_value
                else:
                    return conflict.target_value
            # Default to source if no timestamps
            return conflict.source_value
        
        elif strategy == MergeStrategy.UNION:
            return self._union_values(conflict.source_value, conflict.target_value)
        
        elif strategy == MergeStrategy.INTERSECTION:
            return self._intersect_values(conflict.source_value, conflict.target_value)
        
        elif strategy == MergeStrategy.MANUAL:
            # Return a special marker for manual resolution
            return {
                "__conflict": True,
                "__conflict_type": conflict.conflict_type.value,
                "__source": conflict.source_value,
                "__target": conflict.target_value,
            }
        
        else:
            # Default: target wins
            return conflict.target_value
    
    def _union_values(self, source: Any, target: Any) -> Any:
        """Combine values from both branches."""
        if isinstance(source, list) and isinstance(target, list):
            # Combine lists, removing duplicates
            result = list(source)
            for item in target:
                if item not in result:
                    result.append(item)
            return result
        
        elif isinstance(source, dict) and isinstance(target, dict):
            # Merge dictionaries
            result = dict(source)
            for key, value in target.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._union_values(result[key], value)
                else:
                    result[key] = value
            return result
        
        elif isinstance(source, set) and isinstance(target, set):
            return source | target
        
        else:
            # For scalars, return both in a list
            return [source, target]
    
    def _intersect_values(self, source: Any, target: Any) -> Any:
        """Keep only common elements."""
        if isinstance(source, list) and isinstance(target, list):
            return [item for item in source if item in target]
        
        elif isinstance(source, dict) and isinstance(target, dict):
            return {
                k: source[k]
                for k in source
                if k in target and source[k] == target[k]
            }
        
        elif isinstance(source, set) and isinstance(target, set):
            return source & target
        
        else:
            # For scalars, return if equal
            return source if source == target else None


class StateMerger:
    """
    Merges divergent session states.
    
    Implements three-way merge with conflict detection and resolution.
    """
    
    def __init__(self, resolver: ConflictResolver | None = None):
        self._resolver = resolver or ConflictResolver()
        self._merge_stats: dict[str, int] = {
            "total_merges": 0,
            "conflict_free": 0,
            "with_conflicts": 0,
            "manual_needed": 0,
        }
    
    def merge(
        self,
        source_state: dict[str, Any],
        target_state: dict[str, Any],
        base_state: Optional[dict[str, Any]] = None,
        default_strategy: MergeStrategy = MergeStrategy.TIMESTAMP,
    ) -> MergeResult:
        """
        Perform three-way merge of session states.
        
        Args:
            source_state: Source branch state
            target_state: Target branch state
            base_state: Common ancestor state (optional)
            default_strategy: Default strategy for conflicts
        
        Returns:
            MergeResult with merged state and conflict info
        """
        self._merge_stats["total_merges"] += 1
        
        conflicts: list[Conflict] = []
        resolved: list[Conflict] = []
        unresolved: list[Conflict] = []
        
        merged_state: dict[str, Any] = {}
        all_keys = set(source_state.keys()) | set(target_state.keys())
        
        for key in all_keys:
            source_val = source_state.get(key)
            target_val = target_state.get(key)
            base_val = base_state.get(key) if base_state else None
            
            # No conflict if values are identical
            if self._values_equal(source_val, target_val):
                merged_state[key] = source_val if source_val is not None else target_val
                continue
            
            # Detect conflict type
            conflict_type = self._detect_conflict_type(
                source_val, target_val, base_val, key in source_state, key in target_state
            )
            
            conflict = Conflict(
                key=key,
                conflict_type=conflict_type,
                source_value=source_val,
                target_value=target_val,
                base_value=base_val,
            )
            
            conflicts.append(conflict)
            
            # Attempt resolution
            resolved_value = self._resolver.resolve(conflict, default_strategy)
            
            if isinstance(resolved_value, dict) and resolved_value.get("__conflict"):
                # Manual resolution required
                unresolved.append(conflict)
                # Use target value as placeholder
                merged_state[key] = target_val
            else:
                conflict.resolution = resolved_value
                resolved.append(conflict)
                merged_state[key] = resolved_value
        
        # Update stats
        if not conflicts:
            self._merge_stats["conflict_free"] += 1
        elif unresolved:
            self._merge_stats["manual_needed"] += 1
        else:
            self._merge_stats["with_conflicts"] += 1
        
        return MergeResult(
            success=len(unresolved) == 0,
            merged_state=merged_state,
            conflicts=conflicts,
            resolved_conflicts=resolved,
            unresolved_conflicts=unresolved,
            merge_strategy=default_strategy,
            metadata={
                "source_keys": len(source_state),
                "target_keys": len(target_state),
                "base_keys": len(base_state) if base_state else 0,
                "total_conflicts": len(conflicts),
            },
        )
    
    def _values_equal(self, a: Any, b: Any) -> bool:
        """Check if two values are equal."""
        if type(a) != type(b):
            return False
        
        if isinstance(a, dict):
            if set(a.keys()) != set(b.keys()):
                return False
            return all(self._values_equal(a[k], b[k]) for k in a)
        
        if isinstance(a, list):
            if len(a) != len(b):
                return False
            return all(self._values_equal(x, y) for x, y in zip(a, b))
        
        return a == b
    
    def _detect_conflict_type(
        self,
        source_val: Any,
        target_val: Any,
        base_val: Optional[Any],
        in_source: bool,
        in_target: bool,
    ) -> ConflictType:
        """Detect the type of conflict."""
        # Key added in both
        if base_val is None and in_source and in_target:
            return ConflictType.KEY_ADDED_BOTH
        
        # Key deleted in one, modified in other
        if base_val is not None:
            if not in_source and in_target:
                return ConflictType.KEY_DELETED_MODIFIED
            if in_source and not in_target:
                return ConflictType.KEY_DELETED_MODIFIED
        
        # Type mismatch
        if type(source_val) != type(target_val):
            return ConflictType.TYPE_MISMATCH
        
        # List ordering conflict
        if isinstance(source_val, list) and isinstance(target_val, list):
            if set(source_val) == set(target_val) and source_val != target_val:
                return ConflictType.LIST_ORDER
        
        # Nested structure conflict
        if isinstance(source_val, dict) and isinstance(target_val, dict):
            return ConflictType.NESTED_CONFLICT
        
        # Default: both modified
        return ConflictType.KEY_MODIFIED_BOTH
    
    def merge_parallel_sessions(
        self,
        sessions: list[dict[str, Any]],
        strategy: MergeStrategy = MergeStrategy.TIMESTAMP,
    ) -> MergeResult:
        """
        Merge multiple parallel sessions into a single state.
        
        Performs pairwise merges iteratively.
        """
        if not sessions:
            return MergeResult(
                success=True,
                merged_state={},
                merge_strategy=strategy,
            )
        
        if len(sessions) == 1:
            return MergeResult(
                success=True,
                merged_state=sessions[0],
                merge_strategy=strategy,
            )
        
        # Iteratively merge
        current_state = sessions[0]
        all_conflicts = []
        all_resolved = []
        all_unresolved = []
        
        for i, session in enumerate(sessions[1:], 1):
            result = self.merge(
                current_state,
                session,
                default_strategy=strategy,
            )
            
            current_state = result.merged_state
            all_conflicts.extend(result.conflicts)
            all_resolved.extend(result.resolved_conflicts)
            all_unresolved.extend(result.unresolved_conflicts)
        
        return MergeResult(
            success=len(all_unresolved) == 0,
            merged_state=current_state,
            conflicts=all_conflicts,
            resolved_conflicts=all_resolved,
            unresolved_conflicts=all_unresolved,
            merge_strategy=strategy,
            metadata={
                "session_count": len(sessions),
                "total_conflicts": len(all_conflicts),
            },
        )
    
    def get_conflict_report(self, result: MergeResult) -> str:
        """Generate a human-readable conflict report."""
        lines = [
            "=" * 50,
            "MERGE CONFLICT REPORT",
            "=" * 50,
            f"Merge Strategy: {result.merge_strategy.value}",
            f"Success: {result.success}",
            f"Total Conflicts: {len(result.conflicts)}",
            f"Resolved: {len(result.resolved_conflicts)}",
            f"Unresolved: {len(result.unresolved_conflicts)}",
            "",
        ]
        
        if result.unresolved_conflicts:
            lines.append("UNRESOLVED CONFLICTS (Require Manual Intervention):")
            lines.append("-" * 50)
            for conflict in result.unresolved_conflicts:
                lines.append(f"  Key: {conflict.key}")
                lines.append(f"  Type: {conflict.conflict_type.value}")
                lines.append(f"  Source: {conflict.source_value}")
                lines.append(f"  Target: {conflict.target_value}")
                lines.append("")
        
        if result.resolved_conflicts:
            lines.append("AUTO-RESOLVED CONFLICTS:")
            lines.append("-" * 50)
            for conflict in result.resolved_conflicts:
                lines.append(f"  Key: {conflict.key}")
                lines.append(f"  Strategy: {conflict.strategy_used.value if conflict.strategy_used else 'unknown'}")
                lines.append("")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def get_stats(self) -> dict[str, int]:
        """Get merge statistics."""
        return dict(self._merge_stats)