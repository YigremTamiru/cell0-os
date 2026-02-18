"""
COL-Flow Extractor Module
Cell 0 OS - Cognitive Operating Layer

Multi-request extraction from complex inputs.
Parses user input to identify multiple requests, questions, and tasks.
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set
import json


class RequestType(Enum):
    """Types of requests that can be extracted."""
    QUESTION = auto()          # Information seeking
    ACTION = auto()            # Do something
    CREATION = auto()          # Create content
    ANALYSIS = auto()          # Analyze data
    COMPARISON = auto()        # Compare options
    DECISION = auto()          # Make a choice
    CONFIRMATION = auto()      # Verify something
    CLARIFICATION = auto()     # Ask for clarity
    META = auto()              # About the conversation itself


class RequestPriority(Enum):
    """Priority levels for requests."""
    CRITICAL = 0      # Blockers, must be addressed immediately
    HIGH = 1          # Important, address soon
    MEDIUM = 2        # Normal priority
    LOW = 3           # Can be deferred
    BACKGROUND = 4    # Handle when idle


@dataclass
class ExtractedRequest:
    """A single extracted request from user input."""
    id: str
    type: RequestType
    content: str
    priority: RequestPriority = RequestPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    estimated_tokens: int = 0
    context_refs: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.name,
            "content": self.content,
            "priority": self.priority.name,
            "dependencies": self.dependencies,
            "estimated_tokens": self.estimated_tokens,
            "context_refs": self.context_refs,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class ExtractionResult:
    """Result of extracting requests from input."""
    requests: List[ExtractedRequest]
    raw_input: str
    has_multiple: bool
    ambiguity_score: float  # 0-1, higher = more ambiguous
    suggested_order: List[str]  # Ordered request IDs


class RequestExtractor:
    """
    Extracts multiple requests from complex user inputs.
    
    Handles:
    - Compound sentences with multiple actions
    - Lists of tasks
    - Follow-up questions
    - Implicit vs explicit requests
    - Context references
    """
    
    # Patterns for request separation
    SEPARATORS = [
        r'(?:^|\n)\s*[-•·]\s+',  # Bullet points
        r'(?:^|\n)\s*\d+[.)]\s+',  # Numbered lists
        r'\s*(?:and|plus|also|additionally|furthermore|moreover)\s+(?=(?:can you|could you|please|would you|will you|I need|I want))',
        r'(?:;|\.\s+(?=can you|could you|please|would you|will you|I need|I want|what|how|why|when|where|who))',
    ]
    
    # Request type indicators
    TYPE_PATTERNS = {
        RequestType.QUESTION: [
            r'^(what|why|how|when|where|who|which|is|are|does|do|can|could|would|will|should)\b',
            r'\?\s*$',
        ],
        RequestType.ACTION: [
            r'\b(run|execute|perform|do|make|send|create|update|delete|move|copy|fetch|get)\b',
            r'\b(can you|could you|please|would you|will you)\s+\w+',
        ],
        RequestType.CREATION: [
            r'\b(write|create|generate|build|design|draft|compose|make)\b',
            r'\b(code|script|file|document|report|email|message)\b',
        ],
        RequestType.ANALYSIS: [
            r'\b(analyze|examine|review|investigate|study|assess|evaluate|check)\b',
            r'\b(what does|what is|explain|interpret|break down)\b',
        ],
        RequestType.COMPARISON: [
            r'\b(compare|versus|vs|difference|similarities|better|worse|pros?\s+and\s+cons)\b',
        ],
        RequestType.DECISION: [
            r'\b(should I|which (one|option)|choose|pick|select|decide|recommend)\b',
        ],
        RequestType.CONFIRMATION: [
            r'\b(confirm|verify|check if|make sure|ensure|validate|is that correct)\b',
        ],
        RequestType.CLARIFICATION: [
            r'\b(clarify|elaborate|explain what you mean|I don\'t understand|what do you mean)\b',
        ],
        RequestType.META: [
            r'\b(what did I say|what were we talking about|remind me|earlier you said)\b',
        ],
    }
    
    # Priority indicators
    PRIORITY_PATTERNS = {
        RequestPriority.CRITICAL: [
            r'\b(urgent|emergency|critical|asap|immediately|right now|blocking)\b',
        ],
        RequestPriority.HIGH: [
            r'\b(important|priority|high priority|soon|quickly)\b',
        ],
        RequestPriority.LOW: [
            r'\b(when you get a chance|no rush|low priority|whenever|someday|eventually)\b',
        ],
        RequestPriority.BACKGROUND: [
            r'\b(background|idle|while you\'re at it|also if you could)\b',
        ],
    }
    
    def __init__(self, tokenizer=None):
        """
        Initialize the extractor.
        
        Args:
            tokenizer: Optional tokenizer for token counting
        """
        self.tokenizer = tokenizer
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.separators = [re.compile(p, re.IGNORECASE) for p in self.SEPARATORS]
        self.type_patterns = {
            rt: [re.compile(p, re.IGNORECASE) for p in patterns]
            for rt, patterns in self.TYPE_PATTERNS.items()
        }
        self.priority_patterns = {
            rp: [re.compile(p, re.IGNORECASE) for p in patterns]
            for rp, patterns in self.PRIORITY_PATTERNS.items()
        }
    
    def extract(self, user_input: str, context: Optional[Dict] = None) -> ExtractionResult:
        """
        Extract requests from user input.
        
        Args:
            user_input: Raw user input
            context: Optional context for better extraction
            
        Returns:
            ExtractionResult with extracted requests
        """
        if not user_input or not user_input.strip():
            return ExtractionResult(
                requests=[],
                raw_input=user_input,
                has_multiple=False,
                ambiguity_score=0.0,
                suggested_order=[]
            )
        
        # Split into candidate segments
        segments = self._segment_input(user_input)
        
        # Process each segment into a request
        requests = []
        for i, segment in enumerate(segments):
            if segment.strip():
                request = self._create_request(segment, i, context)
                requests.append(request)
        
        # Detect dependencies
        requests = self._detect_dependencies(requests)
        
        # Calculate ambiguity
        ambiguity = self._calculate_ambiguity(requests, user_input)
        
        # Determine suggested order
        suggested_order = self._suggest_order(requests)
        
        return ExtractionResult(
            requests=requests,
            raw_input=user_input,
            has_multiple=len(requests) > 1,
            ambiguity_score=ambiguity,
            suggested_order=suggested_order
        )
    
    def _segment_input(self, user_input: str) -> List[str]:
        """Split input into candidate segments."""
        segments = [user_input]
        
        for pattern in self.separators:
            new_segments = []
            for seg in segments:
                # Keep the delimiters by using capturing groups
                parts = pattern.split(seg)
                new_segments.extend([p for p in parts if p and p.strip()])
            segments = new_segments
        
        return [s.strip() for s in segments if s.strip()]
    
    def _create_request(self, segment: str, index: int, context: Optional[Dict]) -> ExtractedRequest:
        """Create an ExtractedRequest from a segment."""
        req_id = f"req_{index:03d}"
        
        # Determine type
        req_type = self._detect_type(segment)
        
        # Determine priority
        priority = self._detect_priority(segment)
        
        # Estimate tokens
        tokens = self._estimate_tokens(segment)
        
        # Extract context references
        context_refs = self._extract_context_refs(segment, context)
        
        return ExtractedRequest(
            id=req_id,
            type=req_type,
            content=segment,
            priority=priority,
            estimated_tokens=tokens,
            context_refs=context_refs,
            confidence=1.0
        )
    
    def _detect_type(self, segment: str) -> RequestType:
        """Detect the type of request."""
        scores = {rt: 0 for rt in RequestType}
        
        for req_type, patterns in self.type_patterns.items():
            for pattern in patterns:
                if pattern.search(segment):
                    scores[req_type] += 1
        
        # Return type with highest score, default to ACTION
        max_score = max(scores.values())
        if max_score == 0:
            return RequestType.ACTION
        
        return max(scores.keys(), key=lambda k: scores[k])
    
    def _detect_priority(self, segment: str) -> RequestPriority:
        """Detect priority from segment."""
        for priority, patterns in self.priority_patterns.items():
            for pattern in patterns:
                if pattern.search(segment):
                    return priority
        
        return RequestPriority.MEDIUM
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except:
                pass
        
        # Rough approximation: ~4 chars per token
        return len(text) // 4
    
    def _extract_context_refs(self, segment: str, context: Optional[Dict]) -> List[str]:
        """Extract references to previous context."""
        refs = []
        
        # Pattern: "that", "it", "this", "the file", "the code"
        ref_patterns = [
            r'\b(that|it|this)\s+(?:file|code|document|report|thing)\b',
            r'\b(the|that)\s+(?:previous|earlier|last|above)\b',
            r'\b(same|that)\s+(?:one|thing|file)\b',
        ]
        
        for pattern in ref_patterns:
            if re.search(pattern, segment, re.IGNORECASE):
                refs.append("implicit_ref")
        
        return refs
    
    def _detect_dependencies(self, requests: List[ExtractedRequest]) -> List[ExtractedRequest]:
        """Detect dependencies between requests."""
        # Build a simple dependency graph based on references
        for i, req in enumerate(requests):
            for j, other in enumerate(requests):
                if i != j and i > j:  # Later request depends on earlier
                    # Check for pronoun references
                    if re.search(r'\b(it|that|this|they|them)\b', req.content, re.IGNORECASE):
                        # Check if 'other' produces something that could be referenced
                        if other.type in [RequestType.CREATION, RequestType.ACTION]:
                            req.dependencies.append(other.id)
        
        return requests
    
    def _calculate_ambiguity(self, requests: List[ExtractedRequest], raw_input: str) -> float:
        """Calculate ambiguity score for the extraction."""
        if len(requests) <= 1:
            return 0.0
        
        scores = []
        
        # Check for unclear boundaries
        for req in requests:
            # Low confidence if request is very short
            if len(req.content.split()) < 3:
                scores.append(0.3)
            
            # Check for unclear pronouns
            if re.search(r'\b(it|that|this)\b', req.content, re.IGNORECASE):
                scores.append(0.2)
        
        return min(1.0, sum(scores))
    
    def _suggest_order(self, requests: List[ExtractedRequest]) -> List[str]:
        """Suggest processing order based on dependencies and priority."""
        # Sort by priority first, then dependencies
        # Lower priority number = higher priority
        
        ordered = []
        remaining = set(r.id for r in requests)
        req_map = {r.id: r for r in requests}
        
        while remaining:
            # Find requests with no unmet dependencies
            available = [
                rid for rid in remaining
                if all(dep not in remaining for dep in req_map[rid].dependencies)
            ]
            
            if not available:
                # Circular dependency, just pick one
                available = [next(iter(remaining))]
            
            # Sort by priority
            available.sort(key=lambda rid: req_map[rid].priority.value)
            
            # Take highest priority
            next_id = available[0]
            ordered.append(next_id)
            remaining.remove(next_id)
        
        return ordered
    
    def quick_extract(self, user_input: str) -> List[str]:
        """
        Quick extraction that just returns request strings.
        
        Args:
            user_input: Raw user input
            
        Returns:
            List of request strings
        """
        result = self.extract(user_input)
        return [r.content for r in result.requests]


# Singleton instance for easy import
_default_extractor = None

def get_extractor() -> RequestExtractor:
    """Get or create default extractor instance."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = RequestExtractor()
    return _default_extractor


def extract_requests(user_input: str, context: Optional[Dict] = None) -> ExtractionResult:
    """Convenience function to extract requests."""
    return get_extractor().extract(user_input, context)