"""
COL Request Classifier - Cell 0 OS
Classifies all operations before they execute.
"""

import hashlib
import inspect
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class RequestType(Enum):
    """Classification of request types for COL governance."""
    
    # System operations
    SYSTEM_READ = auto()      # Reading files, config
    SYSTEM_WRITE = auto()     # Writing files, modifying state
    SYSTEM_EXEC = auto()      # Executing shell commands
    SYSTEM_NETWORK = auto()   # Network operations
    
    # Tool operations
    TOOL_BROWSER = auto()     # Browser automation
    TOOL_SEARCH = auto()      # Web search
    TOOL_MESSAGE = auto()     # Sending messages
    TOOL_FILE = auto()        # File operations
    
    # Cognitive operations
    COGNITIVE_ANALYZE = auto()   # Analysis tasks
    COGNITIVE_GENERATE = auto()  # Content generation
    COGNITIVE_REASON = auto()    # Reasoning tasks
    COGNITIVE_PLAN = auto()      # Planning operations
    
    # External operations
    EXTERNAL_API = auto()     # External API calls
    EXTERNAL_SSH = auto()     # SSH operations
    EXTERNAL_DB = auto()      # Database operations
    
    # User operations
    USER_QUERY = auto()       # User questions
    USER_COMMAND = auto()     # Direct commands
    USER_CONVERSATION = auto()  # Conversational
    
    # Meta operations
    META_GOVERNANCE = auto()  # COL internal operations
    META_CHECKPOINT = auto()  # State operations
    META_UNKNOWN = auto()     # Unclassified


@dataclass
class ClassificationResult:
    """Result of request classification."""
    request_type: RequestType
    risk_score: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    features: Dict[str, Any] = field(default_factory=dict)
    signatures: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            'request_type': self.request_type.name,
            'risk_score': self.risk_score,
            'confidence': self.confidence,
            'features': self.features,
            'signatures': self.signatures,
            'timestamp': self.timestamp.isoformat()
        }


class RiskPattern:
    """Pattern for detecting risky operations."""
    
    def __init__(self, name: str, pattern: str, risk_modifier: float, 
                 request_types: Optional[Set[RequestType]] = None):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.risk_modifier = risk_modifier
        self.request_types = request_types or set()
        
    def match(self, text: str) -> bool:
        return bool(self.pattern.search(text))


class RequestClassifier:
    """
    Classifies incoming requests for COL governance.
    
    Uses multiple signals:
    1. Function signature analysis
    2. Argument inspection
    3. Pattern matching
    4. Historical classification cache
    """
    
    # Risk patterns for operation detection
    RISK_PATTERNS = [
        # Destructive operations
        RiskPattern("rm_rf", r"rm\s+-[a-zA-Z]*f[a-zA-Z]*\s+-[a-zA-Z]*r[a-zA-Z]*", 0.9, {RequestType.SYSTEM_EXEC}),
        RiskPattern("delete_all", r"(delete|drop|truncate|destroy).*all|\\*|bulk", 0.85),
        RiskPattern("sudo", r"sudo|administrator|elevated", 0.7, {RequestType.SYSTEM_EXEC}),
        
        # External exposure
        RiskPattern("send_message", r"send|post|tweet|email|broadcast", 0.5, {RequestType.TOOL_MESSAGE, RequestType.EXTERNAL_API}),
        RiskPattern("network_out", r"curl|wget|fetch|request|http|api", 0.4, {RequestType.SYSTEM_NETWORK, RequestType.EXTERNAL_API}),
        
        # File system risks
        RiskPattern("write_config", r"write.*config|override.*settings|modify.*system", 0.6, {RequestType.SYSTEM_WRITE}),
        RiskPattern("read_sensitive", r"password|secret|key|credential|token|auth", 0.5, {RequestType.SYSTEM_READ}),
        
        # Code execution
        RiskPattern("eval_code", r"eval|exec|compile|__import__|subprocess", 0.8, {RequestType.SYSTEM_EXEC}),
        RiskPattern("shell_command", r"bash|sh\s+-c|cmd\.exe|powershell", 0.75, {RequestType.SYSTEM_EXEC}),
        
        # Browser automation
        RiskPattern("browser_action", r"click|submit|fill|type.*input", 0.4, {RequestType.TOOL_BROWSER}),
        
        # Database
        RiskPattern("db_write", r"insert|update|delete.*from|drop\s+table", 0.6, {RequestType.EXTERNAL_DB}),
    ]
    
    # Function name to request type mapping
    FUNCTION_PATTERNS = {
        # File operations
        r'^read_|^load_|^get_file|^fetch': RequestType.SYSTEM_READ,
        r'^write_|^save_|^store_|^update_file': RequestType.SYSTEM_WRITE,
        
        # Execution
        r'^exec|^run_|^shell|^cmd|^subprocess': RequestType.SYSTEM_EXEC,
        
        # Network
        r'^fetch|^request|^download|^upload|^curl': RequestType.SYSTEM_NETWORK,
        
        # Browser
        r'^browse|^click|^navigate|^screenshot|^snapshot': RequestType.TOOL_BROWSER,
        
        # Search
        r'^search|^find|^query|^lookup': RequestType.TOOL_SEARCH,
        
        # Messages
        r'^send|^message|^post|^email|^tweet|^broadcast': RequestType.TOOL_MESSAGE,
        
        # Analysis
        r'^analyze|^classify|^detect|^extract|^parse': RequestType.COGNITIVE_ANALYZE,
        
        # Generation
        r'^generate|^create|^build|^compose|^draft': RequestType.COGNITIVE_GENERATE,
        
        # Planning
        r'^plan|^schedule|^orchestrate|^coordinate': RequestType.COGNITIVE_PLAN,
        
        # Reasoning
        r'^reason|^infer|^deduce|^solve': RequestType.COGNITIVE_REASON,
        
        # APIs
        r'^api_|^call_|^invoke_': RequestType.EXTERNAL_API,
        
        # SSH
        r'^ssh|^remote_|^connect_': RequestType.EXTERNAL_SSH,
        
        # Database
        r'^db_|^sql_|^query_': RequestType.EXTERNAL_DB,
    }
    
    # Base risk scores by type
    BASE_RISK = {
        RequestType.SYSTEM_READ: 0.1,
        RequestType.SYSTEM_WRITE: 0.3,
        RequestType.SYSTEM_EXEC: 0.5,
        RequestType.SYSTEM_NETWORK: 0.2,
        RequestType.TOOL_BROWSER: 0.3,
        RequestType.TOOL_SEARCH: 0.1,
        RequestType.TOOL_MESSAGE: 0.4,
        RequestType.TOOL_FILE: 0.15,
        RequestType.COGNITIVE_ANALYZE: 0.05,
        RequestType.COGNITIVE_GENERATE: 0.1,
        RequestType.COGNITIVE_REASON: 0.05,
        RequestType.COGNITIVE_PLAN: 0.1,
        RequestType.EXTERNAL_API: 0.3,
        RequestType.EXTERNAL_SSH: 0.5,
        RequestType.EXTERNAL_DB: 0.4,
        RequestType.USER_QUERY: 0.0,
        RequestType.USER_COMMAND: 0.15,
        RequestType.USER_CONVERSATION: 0.0,
        RequestType.META_GOVERNANCE: 0.2,
        RequestType.META_CHECKPOINT: 0.1,
        RequestType.META_UNKNOWN: 0.3,
    }
    
    def __init__(self):
        self._classification_cache: Dict[str, ClassificationResult] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
    def _compute_signature(self, operation: Callable, args: tuple, kwargs: dict) -> str:
        """Compute unique signature for operation + arguments."""
        # Get function source/qualname
        func_id = f"{operation.__module__}.{operation.__qualname__}"
        
        # Hash argument types (not values for privacy)
        arg_types = [type(a).__name__ for a in args]
        kwarg_types = {k: type(v).__name__ for k, v in kwargs.items()}
        
        sig_str = f"{func_id}:{arg_types}:{sorted(kwarg_types.items())}"
        return hashlib.sha256(sig_str.encode()).hexdigest()[:16]
    
    def _classify_by_name(self, operation: Callable) -> Optional[RequestType]:
        """Classify based on function name patterns."""
        name = operation.__name__.lower()
        qualname = operation.__qualname__.lower()
        
        for pattern, req_type in self.FUNCTION_PATTERNS.items():
            if re.search(pattern, name) or re.search(pattern, qualname):
                return req_type
        
        return None
    
    def _classify_by_module(self, operation: Callable) -> Optional[RequestType]:
        """Classify based on module path."""
        module = operation.__module__.lower()
        
        if 'browser' in module:
            return RequestType.TOOL_BROWSER
        elif 'search' in module:
            return RequestType.TOOL_SEARCH
        elif 'message' in module or 'discord' in module or 'telegram' in module:
            return RequestType.TOOL_MESSAGE
        elif 'exec' in module or 'subprocess' in module or 'shell' in module:
            return RequestType.SYSTEM_EXEC
        elif 'file' in module or 'os.path' in module or 'pathlib' in module:
            return RequestType.TOOL_FILE
        elif 'db' in module or 'sql' in module:
            return RequestType.EXTERNAL_DB
        elif 'api' in module:
            return RequestType.EXTERNAL_API
        elif 'ssh' in module:
            return RequestType.EXTERNAL_SSH
        elif 'col' in module or 'orchestrator' in module:
            return RequestType.META_GOVERNANCE
            
        return None
    
    def _analyze_arguments(self, args: tuple, kwargs: dict) -> Tuple[float, Dict[str, Any]]:
        """Analyze arguments for risk indicators."""
        risk_modifier = 0.0
        features = {
            'arg_count': len(args),
            'kwarg_count': len(kwargs),
            'patterns_found': [],
            'sensitive_keywords': []
        }
        
        # Convert args to string for pattern matching
        arg_str = str(args) + str(kwargs)
        
        for pattern in self.RISK_PATTERNS:
            if pattern.match(arg_str):
                risk_modifier += pattern.risk_modifier
                features['patterns_found'].append(pattern.name)
        
        # Check for sensitive keywords
        sensitive = ['password', 'secret', 'key', 'token', 'credential', 'private']
        for kw in sensitive:
            if kw in arg_str.lower():
                features['sensitive_keywords'].append(kw)
                risk_modifier += 0.1
        
        return min(risk_modifier, 0.5), features  # Cap at 0.5 from args alone
    
    def _analyze_source(self, operation: Callable) -> Dict[str, Any]:
        """Analyze function source for risk indicators."""
        features = {
            'has_imports': False,
            'uses_eval': False,
            'uses_exec': False,
            'network_calls': [],
            'file_operations': []
        }
        
        try:
            source = inspect.getsource(operation)
            
            # Check for dangerous patterns in source
            if 'eval(' in source or 'ast.literal_eval' in source:
                features['uses_eval'] = True
            if 'exec(' in source:
                features['uses_exec'] = True
            if 'import' in source:
                features['has_imports'] = True
                
            # Detect network calls
            network_patterns = ['requests.', 'urllib', 'http.client', 'socket.']
            for pattern in network_patterns:
                if pattern in source:
                    features['network_calls'].append(pattern)
                    
            # Detect file operations
            file_patterns = ['open(', 'os.remove', 'shutil.', 'pathlib']
            for pattern in file_patterns:
                if pattern in source:
                    features['file_operations'].append(pattern)
                    
        except (OSError, TypeError):
            # Can't get source (built-in, etc.)
            pass
            
        return features
    
    async def classify(
        self,
        operation: Callable,
        args: tuple,
        kwargs: dict,
        context: Any = None
    ) -> ClassificationResult:
        """
        Classify an operation request.
        
        Returns a ClassificationResult with:
        - request_type: The classified type
        - risk_score: 0.0 to 1.0 (higher = riskier)
        - confidence: 0.0 to 1.0 (classification confidence)
        - features: Detected features and patterns
        """
        # Check cache first
        signature = self._compute_signature(operation, args, kwargs)
        if signature in self._classification_cache:
            self._cache_hits += 1
            cached = self._classification_cache[signature]
            # Return copy with updated timestamp
            return ClassificationResult(
                request_type=cached.request_type,
                risk_score=cached.risk_score,
                confidence=cached.confidence,
                features=cached.features.copy(),
                signatures=[signature] + cached.signatures,
                timestamp=datetime.utcnow()
            )
        
        self._cache_misses += 1
        
        # Multi-signal classification
        classifications: List[Tuple[RequestType, float]] = []
        all_features: Dict[str, Any] = {}
        
        # Signal 1: Function name
        name_type = self._classify_by_name(operation)
        if name_type:
            classifications.append((name_type, 0.8))
        
        # Signal 2: Module path
        module_type = self._classify_by_module(operation)
        if module_type:
            classifications.append((module_type, 0.6))
        
        # Signal 3: Argument analysis
        arg_risk, arg_features = self._analyze_arguments(args, kwargs)
        all_features['arguments'] = arg_features
        
        # Signal 4: Source analysis
        source_features = self._analyze_source(operation)
        all_features['source'] = source_features
        
        # Calculate source risk
        source_risk = 0.0
        if source_features['uses_eval']:
            source_risk += 0.3
        if source_features['uses_exec']:
            source_risk += 0.4
        source_risk += len(source_features['network_calls']) * 0.1
        source_risk += len(source_features['file_operations']) * 0.05
        
        # Determine final classification
        if classifications:
            # Weight by confidence and take highest
            best_type = max(classifications, key=lambda x: x[1])[0]
            confidence = sum(c[1] for c in classifications) / len(classifications)
        else:
            best_type = RequestType.META_UNKNOWN
            confidence = 0.3
        
        # Calculate final risk score
        base_risk = self.BASE_RISK.get(best_type, 0.5)
        final_risk = min(1.0, base_risk + arg_risk + source_risk)
        
        # Adjust confidence based on signals
        if name_type and module_type and name_type == module_type:
            confidence = min(1.0, confidence + 0.2)
        
        result = ClassificationResult(
            request_type=best_type,
            risk_score=final_risk,
            confidence=confidence,
            features=all_features,
            signatures=[signature]
        )
        
        # Cache result
        self._classification_cache[signature] = result
        
        return result
    
    def get_stats(self) -> Dict:
        """Get classifier statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': hit_rate,
            'cached_classifications': len(self._classification_cache)
        }
    
    def clear_cache(self):
        """Clear classification cache."""
        self._classification_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0