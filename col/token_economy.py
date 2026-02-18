"""
COL Token Economy - Cell 0 OS
Token budget management and economic decision making.
"""

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .classifier import RequestType


class TokenTransactionType(Enum):
    """Types of token transactions."""
    ALLOCATION = "allocation"      # Budget allocated
    CONSUMPTION = "consumption"    # Tokens consumed
    REFUND = "refund"              # Unused tokens returned
    BONUS = "bonus"                # Bonus tokens awarded
    PENALTY = "penalty"            # Tokens deducted
    TRANSFER = "transfer"          # Transfer between budgets


@dataclass
class TokenTransaction:
    """Record of token movement."""
    transaction_id: str
    type: TokenTransactionType
    amount: int
    balance_before: int
    balance_after: int
    operation_id: Optional[str] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenBudget:
    """Budget allocated for an operation."""
    operation_id: str
    allocated: int
    consumed: int = 0
    reserved: int = 0
    priority: int = 5  # 1-10
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    @property
    def available(self) -> int:
        """Remaining available tokens."""
        return self.allocated - self.consumed - self.reserved
    
    @property
    def required(self) -> int:
        """Minimum tokens required (estimate)."""
        # Required is always less than allocated
        # At minimum, need 10% of allocated or 5 tokens, whichever is higher
        return min(self.allocated, max(5, int(self.allocated * 0.1)))
    
    def can_execute(self) -> bool:
        """Check if operation can execute with available budget."""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return self.available >= self.required
    
    def consume(self, amount: Optional[int] = None) -> int:
        """Consume tokens from budget."""
        if amount is None:
            # Auto-calculate based on typical consumption
            amount = self.required
        
        actual = min(amount, self.available)
        self.consumed += actual
        return actual
    
    def reserve(self, amount: int) -> bool:
        """Reserve tokens for future use."""
        if amount <= self.available:
            self.reserved += amount
            return True
        return False
    
    def release(self, amount: int):
        """Release reserved tokens."""
        self.reserved = max(0, self.reserved - amount)
    
    def to_dict(self) -> Dict:
        return {
            'operation_id': self.operation_id,
            'allocated': self.allocated,
            'consumed': self.consumed,
            'reserved': self.reserved,
            'available': self.available,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class TokenEconomyConfig:
    """Configuration for token economy."""
    
    # Daily token supply (resets at midnight UTC)
    DAILY_SUPPLY = 100_000
    
    # Base costs by request type
    BASE_COSTS = {
        RequestType.SYSTEM_READ: 10,
        RequestType.SYSTEM_WRITE: 50,
        RequestType.SYSTEM_EXEC: 100,
        RequestType.SYSTEM_NETWORK: 30,
        RequestType.TOOL_BROWSER: 75,
        RequestType.TOOL_SEARCH: 20,
        RequestType.TOOL_MESSAGE: 80,
        RequestType.TOOL_FILE: 25,
        RequestType.COGNITIVE_ANALYZE: 40,
        RequestType.COGNITIVE_GENERATE: 60,
        RequestType.COGNITIVE_REASON: 50,
        RequestType.COGNITIVE_PLAN: 45,
        RequestType.EXTERNAL_API: 60,
        RequestType.EXTERNAL_SSH: 90,
        RequestType.EXTERNAL_DB: 70,
        RequestType.USER_QUERY: 5,
        RequestType.USER_COMMAND: 15,
        RequestType.USER_CONVERSATION: 10,
        RequestType.META_GOVERNANCE: 30,
        RequestType.META_CHECKPOINT: 40,
        RequestType.META_UNKNOWN: 50,
    }
    
    # Risk multipliers
    RISK_MULTIPLIERS = {
        (0.0, 0.3): 1.0,    # Low risk
        (0.3, 0.5): 1.2,    # Medium risk
        (0.5, 0.7): 1.5,    # High risk
        (0.7, 0.9): 2.0,    # Very high risk
        (0.9, 1.0): 3.0,    # Critical risk
    }
    
    # Priority bonuses (higher priority = more tokens allocated)
    PRIORITY_MULTIPLIERS = {
        1: 0.5,   # Low priority - fewer resources
        2: 0.7,
        3: 0.8,
        4: 0.9,
        5: 1.0,   # Normal
        6: 1.1,
        7: 1.3,
        8: 1.5,
        9: 1.8,
        10: 2.5,  # Critical - more resources
    }
    
    # Throttling thresholds
    THROTTLE_THRESHOLDS = {
        0.5: 1.0,   # >50% usage - normal
        0.7: 1.5,   # >70% usage - 1.5x cost
        0.85: 2.0,  # >85% usage - 2x cost
        0.95: 3.0,  # >95% usage - 3x cost, start queuing
    }


class TokenEconomy:
    """
    Token-based resource economy for COL.
    
    Manages:
    - Token allocation and consumption
    - Budget tracking per operation
    - Economic throttling under pressure
    - Transaction history
    - Cross-session state persistence
    """
    
    def __init__(self, config: TokenEconomyConfig = None):
        self.config = config or TokenEconomyConfig()
        self._lock = threading.RLock()
        
        # Token accounts
        self._daily_supply = self.config.DAILY_SUPPLY
        self._available_tokens = self._daily_supply
        self._consumed_today = 0
        self._total_consumed = 0
        
        # Active budgets
        self._active_budgets: Dict[str, TokenBudget] = {}
        
        # Transaction history
        self._transactions: List[TokenTransaction] = []
        self._max_transactions = 10000
        
        # Last reset time
        self._last_reset = datetime.utcnow()
        
        # Economic state
        self._economic_pressure = 0.0  # 0.0 - 1.0
        self._throttling_active = False
        
        # Load persisted state
        self._load_state()
        
        # Check for day rollover
        self._check_daily_reset()
    
    def _check_daily_reset(self):
        """Reset daily supply if it's a new day."""
        now = datetime.utcnow()
        if now.date() > self._last_reset.date():
            with self._lock:
                # Archive old stats
                self._log_daily_stats()
                
                # Reset
                self._available_tokens = self._daily_supply
                self._consumed_today = 0
                self._last_reset = now
                self._save_state()
    
    def _log_daily_stats(self):
        """Log daily consumption stats."""
        stats = {
            'date': self._last_reset.date().isoformat(),
            'supply': self._daily_supply,
            'consumed': self._consumed_today,
            'remaining': self._available_tokens,
            'efficiency': self._consumed_today / self._daily_supply if self._daily_supply > 0 else 0
        }
        
        log_path = Path.home() / ".openclaw" / "col" / "token_economy.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(json.dumps(stats) + "\n")
    
    def _get_state_path(self) -> Path:
        """Get path for state persistence."""
        return Path.home() / ".openclaw" / "col" / "token_economy_state.json"
    
    def _save_state(self):
        """Persist token economy state."""
        state = {
            'daily_supply': self._daily_supply,
            'available_tokens': self._available_tokens,
            'consumed_today': self._consumed_today,
            'total_consumed': self._total_consumed,
            'last_reset': self._last_reset.isoformat(),
            'transaction_count': len(self._transactions)
        }
        
        state_path = self._get_state_path()
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, 'w') as f:
            json.dump(state, f)
    
    def _load_state(self):
        """Load persisted token economy state."""
        state_path = self._get_state_path()
        if not state_path.exists():
            return
        
        try:
            with open(state_path) as f:
                state = json.load(f)
            
            self._daily_supply = state.get('daily_supply', self._daily_supply)
            self._available_tokens = state.get('available_tokens', self._available_tokens)
            self._consumed_today = state.get('consumed_today', 0)
            self._total_consumed = state.get('total_consumed', 0)
            self._last_reset = datetime.fromisoformat(state['last_reset'])
        except Exception:
            # Reset to defaults on error
            pass
    
    def get_state(self) -> Dict:
        """Get current token economy state."""
        with self._lock:
            self._check_daily_reset()
            return {
                'daily_supply': self._daily_supply,
                'available_tokens': self._available_tokens,
                'consumed_today': self._consumed_today,
                'total_consumed': self._total_consumed,
                'economic_pressure': self._economic_pressure,
                'throttling_active': self._throttling_active,
                'active_budgets': len(self._active_budgets),
                'transactions_recorded': len(self._transactions)
            }
    
    def _calculate_risk_multiplier(self, risk_score: float) -> float:
        """Get cost multiplier based on risk score."""
        for (low, high), multiplier in self.config.RISK_MULTIPLIERS.items():
            if low <= risk_score < high:
                return multiplier
        return 3.0  # Default to highest for unknown
    
    def _calculate_priority_multiplier(self, priority: int) -> float:
        """Get allocation multiplier based on priority."""
        priority = max(1, min(10, priority))
        return self.config.PRIORITY_MULTIPLIERS.get(priority, 1.0)
    
    def _get_throttle_multiplier(self) -> float:
        """Get current throttling multiplier based on token usage."""
        usage_ratio = 1.0 - (self._available_tokens / self._daily_supply)
        
        # Find applicable threshold
        applicable = 1.0
        for threshold, multiplier in sorted(self.config.THROTTLE_THRESHOLDS.items()):
            if usage_ratio >= threshold:
                applicable = multiplier
        
        return applicable
    
    def allocate_budget(
        self,
        operation_type: RequestType,
        risk_score: float,
        priority: int = 5,
        custom_budget: Optional[int] = None,
        operation_id: Optional[str] = None
    ) -> TokenBudget:
        """
        Allocate a token budget for an operation.
        
        Args:
            operation_type: Type of request
            risk_score: Risk classification (0.0-1.0)
            priority: Priority level (1-10)
            custom_budget: Override calculated budget
            operation_id: Unique operation identifier
        
        Returns:
            TokenBudget for the operation
        """
        self._check_daily_reset()
        
        with self._lock:
            # Calculate base cost
            base_cost = self.config.BASE_COSTS.get(operation_type, 50)
            
            # Apply multipliers
            risk_mult = self._calculate_risk_multiplier(risk_score)
            priority_mult = self._calculate_priority_multiplier(priority)
            throttle_mult = self._get_throttle_multiplier()
            
            # Calculate final allocation
            if custom_budget:
                allocation = custom_budget
            else:
                allocation = int(base_cost * risk_mult * priority_mult * throttle_mult)
            
            # Check if we have enough tokens
            if allocation > self._available_tokens:
                # Allocate what's available (might fail later)
                allocation = self._available_tokens
            
            # Create budget
            budget = TokenBudget(
                operation_id=operation_id or f"op_{int(time.time()*1000)}",
                allocated=allocation,
                priority=priority,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            
            # Reserve tokens
            self._available_tokens -= allocation
            self._active_budgets[budget.operation_id] = budget
            
            # Record transaction
            self._record_transaction(
                TokenTransactionType.ALLOCATION,
                allocation,
                budget.operation_id,
                f"Budget for {operation_type.name}",
                {'risk_score': risk_score, 'priority': priority}
            )
            
            # Update economic pressure
            self._update_economic_pressure()
            
            return budget
    
    def consume_budget(
        self,
        budget_id: str,
        amount: Optional[int] = None,
        actual_cost: Optional[int] = None
    ) -> int:
        """
        Consume tokens from a budget.
        
        Args:
            budget_id: Operation budget ID
            amount: Amount to consume (or auto-calculate)
            actual_cost: Actual cost for reconciliation
        
        Returns:
            Tokens actually consumed
        """
        with self._lock:
            budget = self._active_budgets.get(budget_id)
            if not budget:
                return 0
            
            # Consume from budget
            consumed = budget.consume(amount)
            
            # Track totals
            self._consumed_today += consumed
            self._total_consumed += consumed
            
            # Record transaction
            self._record_transaction(
                TokenTransactionType.CONSUMPTION,
                consumed,
                budget_id,
                "Operation execution",
                {'remaining': budget.available}
            )
            
            # Handle refund for unused budget
            unused = budget.available
            if unused > 0:
                self._available_tokens += unused
                self._record_transaction(
                    TokenTransactionType.REFUND,
                    unused,
                    budget_id,
                    "Unused budget refund"
                )
            
            # Remove budget
            del self._active_budgets[budget_id]
            
            # Update economic pressure
            self._update_economic_pressure()
            self._save_state()
            
            return consumed
    
    def release_budget(self, budget_id: str):
        """Release a budget without consumption (operation cancelled)."""
        with self._lock:
            budget = self._active_budgets.pop(budget_id, None)
            if budget:
                # Return all allocated tokens
                self._available_tokens += budget.allocated
                self._record_transaction(
                    TokenTransactionType.REFUND,
                    budget.allocated,
                    budget_id,
                    "Budget released (cancelled)"
                )
                self._save_state()
    
    def _record_transaction(
        self,
        tx_type: TokenTransactionType,
        amount: int,
        operation_id: str,
        reason: str,
        metadata: Dict = None
    ):
        """Record a token transaction."""
        tx = TokenTransaction(
            transaction_id=f"tx_{int(time.time()*1000000)}",
            type=tx_type,
            amount=amount,
            balance_before=self._available_tokens + (amount if tx_type == TokenTransactionType.CONSUMPTION else -amount),
            balance_after=self._available_tokens,
            operation_id=operation_id,
            reason=reason,
            metadata=metadata or {}
        )
        
        self._transactions.append(tx)
        
        # Trim history if needed
        if len(self._transactions) > self._max_transactions:
            self._transactions = self._transactions[-self._max_transactions:]
    
    def _update_economic_pressure(self):
        """Update economic pressure metrics."""
        usage_ratio = 1.0 - (self._available_tokens / self._daily_supply)
        self._economic_pressure = usage_ratio
        self._throttling_active = usage_ratio > 0.85
    
    def get_budget(self, budget_id: str) -> Optional[TokenBudget]:
        """Get an active budget."""
        return self._active_budgets.get(budget_id)
    
    def get_transactions(
        self,
        operation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[TokenTransaction]:
        """Get transaction history."""
        txs = self._transactions
        if operation_id:
            txs = [t for t in txs if t.operation_id == operation_id]
        return txs[-limit:]
    
    def add_tokens(self, amount: int, reason: str):
        """Add tokens to the economy (e.g., bonus, manual adjustment)."""
        with self._lock:
            self._available_tokens += amount
            self._daily_supply += amount  # Increase daily supply too
            self._record_transaction(
                TokenTransactionType.BONUS,
                amount,
                None,
                reason
            )
            self._save_state()
    
    def penalize(self, amount: int, operation_id: str, reason: str):
        """Apply token penalty."""
        with self._lock:
            self._available_tokens -= amount
            self._record_transaction(
                TokenTransactionType.PENALTY,
                amount,
                operation_id,
                reason
            )
            self._save_state()
    
    def estimate_cost(
        self,
        operation_type: RequestType,
        risk_score: float = 0.0,
        priority: int = 5
    ) -> int:
        """Estimate cost without allocating."""
        base_cost = self.config.BASE_COSTS.get(operation_type, 50)
        risk_mult = self._calculate_risk_multiplier(risk_score)
        priority_mult = self._calculate_priority_multiplier(priority)
        throttle_mult = self._get_throttle_multiplier()
        
        return int(base_cost * risk_mult * priority_mult * throttle_mult)