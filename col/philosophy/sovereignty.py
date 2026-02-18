"""
COL Philosophy - Sovereignty Module
====================================
User sovereignty preservation mechanisms.

This module ensures that user authority remains supreme over the system,
implementing mechanisms for consent, revocation, delegation, and override.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable
from enum import Enum, auto
from datetime import datetime, timedelta
import json
import hashlib

from .principles import PrinciplePriority, get_principle_registry


class ConsentType(Enum):
    """Types of user consent."""
    IMPLICIT = auto()      # Inferred from context
    EXPLICIT = auto()      # Directly stated
    INFORMED = auto()      # With full information
    DELEGATED = auto()     # Delegated to another entity
    PROXY = auto()         # Acting on behalf of user
    EMERGENCY = auto()     # Emergency override (retroactive)
    REVOKED = auto()       # Previously granted but revoked


class DelegationScope(Enum):
    """Scope of user delegation."""
    SINGLE_ACTION = auto()     # One specific action
    CATEGORY = auto()          # Category of actions
    TIME_BOUND = auto()        # For a specific duration
    CONDITIONAL = auto()       # Under specific conditions
    FULL = auto()              # Complete authority (dangerous)


@dataclass
class ConsentRecord:
    """
    Record of user consent for an action or delegation.
    
    Maintains a complete audit trail of consent grants and revocations.
    """
    id: str
    consent_type: ConsentType
    granted_at: datetime
    granted_by: str
    action_id: str
    action_description: str
    scope: Optional[DelegationScope] = None
    expires_at: Optional[datetime] = None
    conditions: List[str] = field(default_factory=list)
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Check if consent is still valid."""
        if self.revoked_at:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True
    
    @property
    def status(self) -> str:
        """Get consent status."""
        if self.revoked_at:
            return "REVOKED"
        if self.expires_at and datetime.now() > self.expires_at:
            return "EXPIRED"
        return "VALID"
    
    def revoke(self, revoked_by: str, reason: str):
        """Revoke this consent."""
        self.revoked_at = datetime.now()
        self.revoked_by = revoked_by
        self.revocation_reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "consent_type": self.consent_type.name,
            "status": self.status,
            "granted_at": self.granted_at.isoformat(),
            "granted_by": self.granted_by,
            "action_id": self.action_id,
            "action_description": self.action_description,
            "scope": self.scope.name if self.scope else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "conditions": self.conditions,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_by": self.revoked_by,
            "revocation_reason": self.revocation_reason,
            "metadata": self.metadata
        }


@dataclass
class DelegationRecord:
    """
    Record of authority delegation from user to system or others.
    
    Tracks what authority has been delegated and under what conditions.
    """
    id: str
    delegator: str
    delegate: str
    scope: DelegationScope
    granted_at: datetime
    expires_at: Optional[datetime]
    permissions: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    active: bool = True
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Check if delegation is valid."""
        if not self.active or self.revoked_at:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True
    
    def revoke(self, revoked_by: str):
        """Revoke this delegation."""
        self.active = False
        self.revoked_at = datetime.now()
        self.revoked_by = revoked_by
    
    def has_permission(self, permission: str) -> bool:
        """Check if delegation includes a specific permission."""
        if not self.is_valid:
            return False
        return permission in self.permissions or "*" in self.permissions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "delegator": self.delegator,
            "delegate": self.delegate,
            "scope": self.scope.name,
            "is_valid": self.is_valid,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "permissions": self.permissions,
            "restrictions": self.restrictions,
            "conditions": self.conditions,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None
        }


class SovereigntyManager:
    """
    Manages user sovereignty across the COL.
    
    Ensures that:
    1. User directives take precedence
    2. Consent is properly tracked
    3. Delegations are managed
    4. Revocations are honored immediately
    5. System never overrides user without justification
    """
    
    def __init__(self):
        self._consents: Dict[str, ConsentRecord] = {}
        self._delegations: Dict[str, DelegationRecord] = {}
        self._user_preferences: Dict[str, Any] = {}
        self._override_log: List[Dict[str, Any]] = []
    
    def record_consent(self, user_id: str, action_id: str,
                      action_description: str,
                      consent_type: ConsentType = ConsentType.EXPLICIT,
                      scope: Optional[DelegationScope] = None,
                      duration_minutes: Optional[int] = None,
                      conditions: Optional[List[str]] = None) -> ConsentRecord:
        """
        Record user consent for an action.
        
        Args:
            user_id: The user granting consent
            action_id: Unique identifier for the action
            action_description: Human-readable description
            consent_type: Type of consent
            scope: Scope of consent
            duration_minutes: How long consent is valid (None = indefinite)
            conditions: Conditions under which consent applies
        
        Returns:
            ConsentRecord
        """
        consent_id = self._generate_id(user_id, action_id)
        
        expires = None
        if duration_minutes:
            expires = datetime.now() + timedelta(minutes=duration_minutes)
        
        record = ConsentRecord(
            id=consent_id,
            consent_type=consent_type,
            granted_at=datetime.now(),
            granted_by=user_id,
            action_id=action_id,
            action_description=action_description,
            scope=scope,
            expires_at=expires,
            conditions=conditions or []
        )
        
        self._consents[consent_id] = record
        return record
    
    def check_consent(self, user_id: str, action_id: str) -> Optional[ConsentRecord]:
        """
        Check if valid consent exists for an action.
        
        Returns the consent record if valid, None otherwise.
        """
        consent_id = self._generate_id(user_id, action_id)
        record = self._consents.get(consent_id)
        
        if record and record.is_valid:
            return record
        return None
    
    def revoke_consent(self, consent_id: str, revoked_by: str, 
                      reason: str) -> bool:
        """
        Revoke previously granted consent.
        
        Returns True if revocation successful.
        """
        record = self._consents.get(consent_id)
        if not record:
            return False
        
        record.revoke(revoked_by, reason)
        return True
    
    def revoke_all_consent(self, user_id: str, revoked_by: str,
                          reason: str) -> int:
        """
        Revoke all consent for a user.
        
        Returns count of consents revoked.
        """
        count = 0
        for record in self._consents.values():
            if record.granted_by == user_id and record.is_valid:
                record.revoke(revoked_by, reason)
                count += 1
        return count
    
    def create_delegation(self, delegator: str, delegate: str,
                         scope: DelegationScope,
                         permissions: List[str],
                         duration_minutes: Optional[int] = None,
                         restrictions: Optional[List[str]] = None,
                         conditions: Optional[List[str]] = None) -> DelegationRecord:
        """
        Create a delegation of authority.
        
        Args:
            delegator: User delegating authority
            delegate: Entity receiving authority (e.g., "system", "agent:123")
            scope: Scope of delegation
            permissions: List of delegated permissions
            duration_minutes: How long delegation lasts
            restrictions: Explicit restrictions
            conditions: Conditions for delegation
        
        Returns:
            DelegationRecord
        """
        delegation_id = self._generate_id(delegator, delegate)
        
        expires = None
        if duration_minutes:
            expires = datetime.now() + timedelta(minutes=duration_minutes)
        
        # Validate scope - FULL delegation requires explicit warning
        if scope == DelegationScope.FULL:
            # Log this dangerous delegation
            self._log_override(
                "FULL_DELEGATION",
                delegator,
                f"Full authority delegated to {delegate}",
                "CRITICAL"
            )
        
        record = DelegationRecord(
            id=delegation_id,
            delegator=delegator,
            delegate=delegate,
            scope=scope,
            granted_at=datetime.now(),
            expires_at=expires,
            permissions=permissions,
            restrictions=restrictions or [],
            conditions=conditions or []
        )
        
        self._delegations[delegation_id] = record
        return record
    
    def check_delegation(self, delegator: str, delegate: str,
                        permission: str) -> Optional[DelegationRecord]:
        """
        Check if valid delegation exists for a permission.
        
        Returns the delegation record if valid, None otherwise.
        """
        delegation_id = self._generate_id(delegator, delegate)
        record = self._delegations.get(delegation_id)
        
        if record and record.is_valid and record.has_permission(permission):
            return record
        return None
    
    def revoke_delegation(self, delegation_id: str, revoked_by: str) -> bool:
        """Revoke a delegation."""
        record = self._delegations.get(delegation_id)
        if not record:
            return False
        
        record.revoke(revoked_by)
        return True
    
    def revoke_all_delegations(self, delegator: str, revoked_by: str) -> int:
        """Revoke all delegations from a user."""
        count = 0
        for record in self._delegations.values():
            if record.delegator == delegator and record.is_valid:
                record.revoke(revoked_by)
                count += 1
        return count
    
    def assert_sovereignty(self, user_id: str, directive: str,
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assert user sovereignty over a directive.
        
        This is the core sovereignty mechanism - ensures user directives
        override any system recommendations or defaults.
        
        Returns:
            Dict with sovereignty assertion result
        """
        result = {
            "user_id": user_id,
            "directive": directive,
            "asserted_at": datetime.now().isoformat(),
            "effective": True,
            "overrides": [],
            "notifications": []
        }
        
        # Check for any conflicting system actions
        # (In real implementation, would check active operations)
        
        # Log the assertion
        self._log_override(
            "SOVEREIGNTY_ASSERTION",
            user_id,
            directive,
            "INFO"
        )
        
        # Cancel any conflicting delegated operations
        cancelled = self._cancel_conflicting_delegations(user_id, directive)
        if cancelled:
            result["overrides"] = cancelled
            result["notifications"].append(
                f"Cancelled {len(cancelled)} conflicting delegated operations"
            )
        
        return result
    
    def can_system_override(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if system can override user in this context.
        
        Returns (can_override, reason).
        
        System can only override in life-critical situations where
        user direction would cause immediate harm.
        """
        # Check for life-critical situation
        if context.get("life_threatening", False):
            return True, "Life-threatening situation - safety override justified"
        
        # Check for emergency
        if context.get("emergency", False) and context.get("immediate_harm", False):
            return True, "Emergency with immediate harm risk"
        
        # Check for incapacity
        if context.get("user_incapacitated", False):
            return True, "User incapacitated - acting in best interest"
        
        return False, "No justification for override - user sovereignty preserved"
    
    def record_system_override(self, user_id: str, action: str,
                              justification: str, context: Dict[str, Any]):
        """
        Record when system has overridden user.
        
        This should be rare and always require strong justification.
        """
        self._log_override(
            "SYSTEM_OVERRIDE",
            user_id,
            action,
            "CRITICAL",
            justification=justification,
            context=context
        )
        
        # Immediate notification required
        # (In real implementation, would send to notification system)
    
    def set_user_preference(self, user_id: str, key: str, value: Any):
        """Set a user preference."""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][key] = {
            "value": value,
            "set_at": datetime.now().isoformat()
        }
    
    def get_user_preference(self, user_id: str, key: str, 
                           default: Any = None) -> Any:
        """Get a user preference."""
        user_prefs = self._user_preferences.get(user_id, {})
        pref = user_prefs.get(key, {})
        return pref.get("value", default)
    
    def get_user_consents(self, user_id: str, 
                         include_expired: bool = False) -> List[ConsentRecord]:
        """Get all consent records for a user."""
        records = [r for r in self._consents.values() 
                  if r.granted_by == user_id]
        if not include_expired:
            records = [r for r in records if r.status == "VALID"]
        return records
    
    def get_user_delegations(self, user_id: str,
                            include_expired: bool = False) -> List[DelegationRecord]:
        """Get all delegations for a user."""
        records = [r for r in self._delegations.values()
                  if r.delegator == user_id]
        if not include_expired:
            records = [r for r in records if r.is_valid]
        return records
    
    def get_sovereignty_report(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive sovereignty report for a user."""
        return {
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "active_consents": len(self.get_user_consents(user_id)),
            "active_delegations": len(self.get_user_delegations(user_id)),
            "preferences_count": len(self._user_preferences.get(user_id, {})),
            "override_history": [
                log for log in self._override_log
                if log.get("user_id") == user_id
            ]
        }
    
    def _generate_id(self, *parts) -> str:
        """Generate unique ID from parts."""
        content = ":".join(str(p) for p in parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _log_override(self, event_type: str, user_id: str, 
                     action: str, severity: str,
                     justification: str = None, context: Dict = None):
        """Log a sovereignty-related event."""
        self._override_log.append({
            "event_type": event_type,
            "user_id": user_id,
            "action": action,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "justification": justification,
            "context": context
        })
    
    def _cancel_conflicting_delegations(self, user_id: str, 
                                       directive: str) -> List[str]:
        """Cancel any delegated operations that conflict with user directive."""
        cancelled = []
        
        for record in self._delegations.values():
            if record.delegator == user_id and record.is_valid:
                # Check if delegation conflicts with directive
                # (Simplified - would check actual operation in real impl)
                if self._conflicts_with(directive, record):
                    record.revoke(user_id)
                    cancelled.append(record.id)
        
        return cancelled
    
    def _conflicts_with(self, directive: str, delegation: DelegationRecord) -> bool:
        """Check if directive conflicts with delegation."""
        # Simplified conflict detection
        # In real implementation, would analyze semantic content
        return True  # Conservative: assume conflict
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all sovereignty data for a user (GDPR-style)."""
        return {
            "user_id": user_id,
            "exported_at": datetime.now().isoformat(),
            "consents": [c.to_dict() for c in self._consents.values()
                        if c.granted_by == user_id],
            "delegations": [d.to_dict() for d in self._delegations.values()
                           if d.delegator == user_id],
            "preferences": self._user_preferences.get(user_id, {}),
            "override_log": [log for log in self._override_log
                           if log.get("user_id") == user_id]
        }
    
    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all sovereignty data for a user (right to be forgotten).
        
        Retains minimal audit logs as required by law.
        """
        # Delete consents
        self._consents = {k: v for k, v in self._consents.items()
                         if v.granted_by != user_id}
        
        # Delete delegations
        self._delegations = {k: v for k, v in self._delegations.items()
                            if v.delegator != user_id}
        
        # Delete preferences
        if user_id in self._user_preferences:
            del self._user_preferences[user_id]
        
        # Anonymize override log (keep for audit, remove PII)
        for log in self._override_log:
            if log.get("user_id") == user_id:
                log["user_id"] = "[REDACTED]"
        
        return True


# Global manager instance
_manager: Optional[SovereigntyManager] = None


def get_sovereignty_manager() -> SovereigntyManager:
    """Get global sovereignty manager."""
    global _manager
    if _manager is None:
        _manager = SovereigntyManager()
    return _manager


# Convenience functions

def record_consent(user_id: str, action_id: str, action_description: str,
                  **kwargs) -> ConsentRecord:
    """Record user consent."""
    return get_sovereignty_manager().record_consent(
        user_id, action_id, action_description, **kwargs
    )


def check_consent(user_id: str, action_id: str) -> Optional[ConsentRecord]:
    """Check for valid consent."""
    return get_sovereignty_manager().check_consent(user_id, action_id)


def assert_sovereignty(user_id: str, directive: str, 
                      context: Dict[str, Any]) -> Dict[str, Any]:
    """Assert user sovereignty."""
    return get_sovereignty_manager().assert_sovereignty(user_id, directive, context)


def can_override(context: Dict[str, Any]) -> tuple[bool, str]:
    """Check if system can override user."""
    return get_sovereignty_manager().can_system_override(context)