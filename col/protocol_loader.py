"""
COL Protocol Loader - Cell 0 OS
Dynamic protocol loading based on classification.
"""

import importlib
import json
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .classifier import ClassificationResult, RequestType


class ProtocolPriority(Enum):
    """Protocol enforcement levels."""
    ADVISORY = "advisory"      # Suggestions only
    STANDARD = "standard"      # Standard enforcement
    STRICT = "strict"          # Strict enforcement
    CRITICAL = "critical"      # Cannot override


@dataclass
class ProtocolRule:
    """Individual protocol rule."""
    name: str
    condition: str  # Python expression or pattern
    action: str     # allow, deny, confirm, throttle
    message: Optional[str] = None
    priority: ProtocolPriority = ProtocolPriority.STANDARD


@dataclass
class Protocol:
    """A governance protocol."""
    id: str
    name: str
    version: str
    description: str
    applies_to: List[RequestType]
    priority: ProtocolPriority
    rules: List[ProtocolRule] = field(default_factory=list)
    pre_hooks: List[str] = field(default_factory=list)
    post_hooks: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'applies_to': [t.name for t in self.applies_to],
            'priority': self.priority.value,
            'rules_count': len(self.rules),
            'config': self.config
        }


class ProtocolAction(Enum):
    """Actions a protocol can take."""
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"      # Require user confirmation
    THROTTLE = "throttle"    # Rate limit
    ENHANCE = "enhance"      # Add extra checks
    LOG = "log"              # Extra logging
    CHECKPOINT = "checkpoint"  # Force checkpoint


@dataclass
class ProtocolDecision:
    """Decision from protocol evaluation."""
    action: ProtocolAction
    protocol_id: str
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseProtocol(ABC):
    """Base class for dynamic protocol implementations."""
    
    PROTOCOL_ID: str = "base"
    PROTOCOL_NAME: str = "Base Protocol"
    VERSION: str = "1.0"
    APPLIES_TO: List[RequestType] = []
    PRIORITY: ProtocolPriority = ProtocolPriority.STANDARD
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = True
    
    @abstractmethod
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        """Evaluate if this protocol applies and return decision."""
        pass
    
    def on_load(self):
        """Called when protocol is loaded."""
        pass
    
    def on_unload(self):
        """Called when protocol is unloaded."""
        pass


# =============================================================================
# BUILTIN PROTOCOLS
# =============================================================================

class HighRiskProtocol(BaseProtocol):
    """Protocol for high-risk operations."""
    
    PROTOCOL_ID = "high_risk"
    PROTOCOL_NAME = "High Risk Operation Protocol"
    VERSION = "1.0"
    APPLIES_TO = list(RequestType)
    PRIORITY = ProtocolPriority.CRITICAL
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        if classification.risk_score > 0.8:
            return ProtocolDecision(
                action=ProtocolAction.CHECKPOINT,
                protocol_id=self.PROTOCOL_ID,
                reason=f"Risk score {classification.risk_score:.2f} exceeds threshold",
                metadata={'requires_confirmation': True}
            )
        return None


class DestructiveOperationProtocol(BaseProtocol):
    """Protocol for destructive operations."""
    
    PROTOCOL_ID = "destructive_ops"
    PROTOCOL_NAME = "Destructive Operation Protocol"
    VERSION = "1.0"
    APPLIES_TO = [RequestType.SYSTEM_WRITE, RequestType.SYSTEM_EXEC, RequestType.EXTERNAL_DB]
    PRIORITY = ProtocolPriority.STRICT
    
    DESTRUCTIVE_PATTERNS = [
        'delete', 'remove', 'drop', 'truncate', 'destroy', 
        'rm ', 'del ', 'format', 'wipe'
    ]
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        features = classification.features
        
        # Check for destructive patterns
        arg_features = features.get('arguments', {})
        patterns = arg_features.get('patterns_found', [])
        
        if any(p.startswith(('rm_', 'delete_')) for p in patterns):
            return ProtocolDecision(
                action=ProtocolAction.CONFIRM,
                protocol_id=self.PROTOCOL_ID,
                reason="Destructive operation detected",
                metadata={'destructive_patterns': patterns}
            )
        
        return None


class ExternalCommunicationProtocol(BaseProtocol):
    """Protocol for external communications."""
    
    PROTOCOL_ID = "external_comms"
    PROTOCOL_NAME = "External Communication Protocol"
    VERSION = "1.0"
    APPLIES_TO = [RequestType.TOOL_MESSAGE, RequestType.EXTERNAL_API, RequestType.SYSTEM_NETWORK]
    PRIORITY = ProtocolPriority.STANDARD
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        
        if classification.request_type == RequestType.TOOL_MESSAGE:
            return ProtocolDecision(
                action=ProtocolAction.ENHANCE,
                protocol_id=self.PROTOCOL_ID,
                reason="External message - enhancing validation",
                metadata={'log_level': 'high'}
            )
        
        if classification.request_type == RequestType.EXTERNAL_API:
            return ProtocolDecision(
                action=ProtocolAction.THROTTLE,
                protocol_id=self.PROTOCOL_ID,
                reason="API call - applying rate limiting",
                metadata={'max_requests_per_minute': 60}
            )
        
        return None


class TokenEconomyProtocol(BaseProtocol):
    """Protocol for token budget enforcement."""
    
    PROTOCOL_ID = "token_economy"
    PROTOCOL_NAME = "Token Economy Protocol"
    VERSION = "1.0"
    APPLIES_TO = list(RequestType)
    PRIORITY = ProtocolPriority.STRICT
    
    COST_MULTIPLIERS = {
        RequestType.SYSTEM_EXEC: 2.0,
        RequestType.TOOL_BROWSER: 1.5,
        RequestType.EXTERNAL_API: 1.3,
        RequestType.COGNITIVE_GENERATE: 1.5,
        RequestType.COGNITIVE_REASON: 1.2,
    }
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        # This protocol provides metadata for token economy
        multiplier = self.COST_MULTIPLIERS.get(classification.request_type, 1.0)
        
        return ProtocolDecision(
            action=ProtocolAction.ENHANCE,
            protocol_id=self.PROTOCOL_ID,
            reason="Applying token cost multiplier",
            metadata={
                'cost_multiplier': multiplier,
                'base_cost': 100,
                'request_type': classification.request_type.name
            }
        )


class ResourcePressureProtocol(BaseProtocol):
    """Protocol for resource pressure management."""
    
    PROTOCOL_ID = "resource_pressure"
    PROTOCOL_NAME = "Resource Pressure Protocol"
    VERSION = "1.0"
    APPLIES_TO = list(RequestType)
    PRIORITY = ProtocolPriority.STRICT
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        # This would check current resource pressure
        # For now, return advisory action
        return ProtocolDecision(
            action=ProtocolAction.LOG,
            protocol_id=self.PROTOCOL_ID,
            reason="Monitoring resource pressure",
            metadata={'check_pressure': True}
        )


class CheckpointProtocol(BaseProtocol):
    """Protocol for automatic checkpointing."""
    
    PROTOCOL_ID = "checkpointing"
    PROTOCOL_NAME = "Automatic Checkpointing Protocol"
    VERSION = "1.0"
    APPLIES_TO = [RequestType.SYSTEM_WRITE, RequestType.SYSTEM_EXEC, RequestType.EXTERNAL_DB]
    PRIORITY = ProtocolPriority.STANDARD
    
    CHECKPOINT_INTERVALS = {
        RequestType.SYSTEM_WRITE: 10,    # Every 10 writes
        RequestType.SYSTEM_EXEC: 5,      # Every 5 executions
        RequestType.EXTERNAL_DB: 5,      # Every 5 DB ops
    }
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self._operation_counts: Dict[RequestType, int] = {}
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        
        # Count operations
        self._operation_counts[classification.request_type] = \
            self._operation_counts.get(classification.request_type, 0) + 1
        
        interval = self.CHECKPOINT_INTERVALS.get(classification.request_type, 20)
        
        if self._operation_counts[classification.request_type] % interval == 0:
            return ProtocolDecision(
                action=ProtocolAction.CHECKPOINT,
                protocol_id=self.PROTOCOL_ID,
                reason=f"Checkpoint interval reached ({interval} operations)",
                metadata={
                    'operation_count': self._operation_counts[classification.request_type]
                }
            )
        
        return None


class AuditLoggingProtocol(BaseProtocol):
    """Protocol for comprehensive audit logging."""
    
    PROTOCOL_ID = "audit_logging"
    PROTOCOL_NAME = "Audit Logging Protocol"
    VERSION = "1.0"
    APPLIES_TO = [
        RequestType.SYSTEM_EXEC, RequestType.EXTERNAL_API,
        RequestType.TOOL_MESSAGE, RequestType.SYSTEM_WRITE
    ]
    PRIORITY = ProtocolPriority.STANDARD
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        return ProtocolDecision(
            action=ProtocolAction.LOG,
            protocol_id=self.PROTOCOL_ID,
            reason="High-audit operation - detailed logging enabled",
            metadata={
                'log_args': False,  # Don't log actual values for privacy
                'log_classification': True,
                'log_result': True,
                'retention_days': 30
            }
        )


class PrivacyProtocol(BaseProtocol):
    """Protocol for privacy protection."""
    
    PROTOCOL_ID = "privacy"
    PROTOCOL_NAME = "Privacy Protection Protocol"
    VERSION = "1.0"
    APPLIES_TO = list(RequestType)
    PRIORITY = ProtocolPriority.CRITICAL
    
    SENSITIVE_PATTERNS = [
        'password', 'secret', 'key', 'token', 'credential',
        'private', 'ssn', 'credit_card', 'api_key'
    ]
    
    def evaluate(self, classification: ClassificationResult, 
                 context: Any) -> Optional[ProtocolDecision]:
        
        features = classification.features
        arg_features = features.get('arguments', {})
        sensitive = arg_features.get('sensitive_keywords', [])
        
        if sensitive:
            return ProtocolDecision(
                action=ProtocolAction.ENHANCE,
                protocol_id=self.PROTOCOL_ID,
                reason=f"Sensitive keywords detected: {sensitive}",
                metadata={
                    'redact_logs': True,
                    'encrypt_checkpoint': True,
                    'sensitive_fields': sensitive
                }
            )
        
        return None


# =============================================================================
# PROTOCOL LOADER
# =============================================================================

class ProtocolLoader:
    """
    Dynamic protocol loading system.
    
    Loads protocols from:
    1. Built-in protocols (defined above)
    2. Custom protocol modules (dynamically imported)
    3. Protocol configuration files (JSON)
    """
    
    BUILTIN_PROTOCOLS = [
        HighRiskProtocol,
        DestructiveOperationProtocol,
        ExternalCommunicationProtocol,
        TokenEconomyProtocol,
        ResourcePressureProtocol,
        CheckpointProtocol,
        AuditLoggingProtocol,
        PrivacyProtocol,
    ]
    
    def __init__(self):
        self._protocols: Dict[str, BaseProtocol] = {}
        self._protocols_by_type: Dict[RequestType, List[BaseProtocol]] = {}
        self._load_builtin_protocols()
        self._load_custom_protocols()
        
    def _load_builtin_protocols(self):
        """Load all built-in protocols."""
        for protocol_class in self.BUILTIN_PROTOCOLS:
            try:
                instance = protocol_class()
                instance.on_load()
                self._register_protocol(instance)
            except Exception as e:
                print(f"Failed to load protocol {protocol_class.PROTOCOL_ID}: {e}")
    
    def _load_custom_protocols(self):
        """Load custom protocols from filesystem."""
        # Look for custom protocols in ~/.openclaw/col/protocols/
        protocols_dir = Path.home() / ".openclaw" / "col" / "protocols"
        if not protocols_dir.exists():
            return
        
        # Load Python protocol modules
        for file_path in protocols_dir.glob("*_protocol.py"):
            try:
                self._load_protocol_module(file_path)
            except Exception as e:
                print(f"Failed to load protocol module {file_path}: {e}")
        
        # Load JSON protocol configs
        for file_path in protocols_dir.glob("*.json"):
            try:
                self._load_protocol_config(file_path)
            except Exception as e:
                print(f"Failed to load protocol config {file_path}: {e}")
    
    def _load_protocol_module(self, file_path: Path):
        """Load a protocol from a Python module."""
        spec = importlib.util.spec_from_file_location(
            f"custom_protocol_{file_path.stem}", file_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find protocol classes
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, BaseProtocol) and 
                obj is not BaseProtocol):
                instance = obj()
                instance.on_load()
                self._register_protocol(instance)
    
    def _load_protocol_config(self, file_path: Path):
        """Load a protocol from JSON configuration."""
        with open(file_path) as f:
            config = json.load(f)
        
        # Create protocol from config
        rules = [
            ProtocolRule(**rule) for rule in config.get('rules', [])
        ]
        
        protocol = Protocol(
            id=config['id'],
            name=config['name'],
            version=config.get('version', '1.0'),
            description=config.get('description', ''),
            applies_to=[RequestType[t] for t in config.get('applies_to', [])],
            priority=ProtocolPriority(config.get('priority', 'standard')),
            rules=rules,
            config=config.get('config', {})
        )
        
        # Store as static protocol (not dynamic class)
        self._static_protocols[protocol.id] = protocol
    
    def _register_protocol(self, protocol: BaseProtocol):
        """Register a loaded protocol."""
        self._protocols[protocol.PROTOCOL_ID] = protocol
        
        # Index by request type
        for req_type in protocol.APPLIES_TO:
            if req_type not in self._protocols_by_type:
                self._protocols_by_type[req_type] = []
            self._protocols_by_type[req_type].append(protocol)
    
    def load(self, classification: ClassificationResult, 
             governance: Dict) -> Optional[Protocol]:
        """
        Load applicable protocols for a classification.
        
        Returns a composite protocol or None.
        """
        req_type = classification.request_type
        
        # Get protocols for this request type
        applicable = self._protocols_by_type.get(req_type, [])
        
        # Also include universal protocols
        universal = self._protocols_by_type.get(None, [])
        
        all_protocols = applicable + universal
        
        if not all_protocols:
            return None
        
        # Sort by priority
        priority_order = {
            ProtocolPriority.CRITICAL: 0,
            ProtocolPriority.STRICT: 1,
            ProtocolPriority.STANDARD: 2,
            ProtocolPriority.ADVISORY: 3
        }
        all_protocols.sort(key=lambda p: priority_order.get(p.PRIORITY, 2))
        
        # Evaluate protocols and collect decisions
        rules = []
        for proto in all_protocols:
            if not proto.enabled:
                continue
            
            decision = proto.evaluate(classification, None)
            if decision:
                rule = ProtocolRule(
                    name=f"{proto.PROTOCOL_ID}_rule",
                    condition="auto_evaluated",
                    action=decision.action.value,
                    message=decision.reason,
                    priority=proto.PRIORITY
                )
                rules.append(rule)
        
        if not rules:
            return None
        
        # Build composite protocol
        return Protocol(
            id=f"composite_{req_type.name.lower()}",
            name=f"Composite Protocol for {req_type.name}",
            version="1.0",
            description=f"Dynamically generated protocol for {req_type.name}",
            applies_to=[req_type],
            priority=ProtocolPriority.STANDARD,
            rules=rules
        )
    
    def get_protocol(self, protocol_id: str) -> Optional[BaseProtocol]:
        """Get a loaded protocol by ID."""
        return self._protocols.get(protocol_id)
    
    def list_protocols(self) -> List[Dict]:
        """List all loaded protocols."""
        return [
            {
                'id': p.PROTOCOL_ID,
                'name': p.PROTOCOL_NAME,
                'version': p.VERSION,
                'applies_to': [t.name for t in p.APPLIES_TO],
                'priority': p.PRIORITY.value,
                'enabled': p.enabled
            }
            for p in self._protocols.values()
        ]
    
    def enable_protocol(self, protocol_id: str):
        """Enable a protocol."""
        if protocol_id in self._protocols:
            self._protocols[protocol_id].enabled = True
    
    def disable_protocol(self, protocol_id: str):
        """Disable a protocol."""
        if protocol_id in self._protocols:
            self._protocols[protocol_id].enabled = False
    
    def reload(self):
        """Reload all protocols."""
        # Unload existing
        for proto in self._protocols.values():
            proto.on_unload()
        
        self._protocols.clear()
        self._protocols_by_type.clear()
        
        # Reload
        self._load_builtin_protocols()
        self._load_custom_protocols()