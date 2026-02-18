"""
Search Result Ranking and Filtering for Cell 0 OS

Provides intelligent ranking algorithms:
- Relevance scoring
- Diversity ranking
- Recency boosting
- Quality filtering
- Duplicate detection
"""

import re
import math
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter
import logging

logger = logging.getLogger("cell0.search.ranker")


@dataclass
class RankedResult:
    """Result with ranking information"""
    result: Any
    relevance_score: float = 0.0
    diversity_score: float = 0.0
    recency_score: float = 0.0
    quality_score: float = 0.0
    final_score: float = 0.0
    ranking_factors: Dict[str, float] = field(default_factory=dict)


class ResultRanker:
    """
    Intelligent result ranker with multiple strategies
    
    Supports:
    - TF-IDF based relevance scoring
    - MMR (Maximal Marginal Relevance) for diversity
    - Recency boosting for time-sensitive content
    - Quality heuristics
    """
    
    def __init__(
        self,
        relevance_weight: float = 0.4,
        diversity_weight: float = 0.2,
        recency_weight: float = 0.2,
        quality_weight: float = 0.2,
    ):
        """
        Initialize ranker
        
        Args:
            relevance_weight: Weight for relevance scoring
            diversity_weight: Weight for diversity scoring
            recency_weight: Weight for recency boosting
            quality_weight: Weight for quality heuristics
        """
        self.weights = {
            "relevance": relevance_weight,
            "diversity": diversity_weight,
            "recency": recency_weight,
            "quality": quality_weight,
        }
    
    def rank(
        self,
        results: List[Any],
        query: str,
        enable_diversity: bool = True,
        enable_recency: bool = True,
    ) -> List[RankedResult]:
        """
        Rank results using multiple factors
        
        Args:
            results: List of search results
            query: Original search query
            enable_diversity: Whether to apply diversity ranking
            enable_recency: Whether to boost recent results
            
        Returns:
            List of ranked results
        """
        if not results:
            return []
        
        # Calculate individual scores
        relevance_scores = self._calculate_relevance(results, query)
        quality_scores = self._calculate_quality(results)
        recency_scores = self._calculate_recency(results) if enable_recency else [0.5] * len(results)
        
        # Initialize ranked results
        ranked = []
        for i, result in enumerate(results):
            ranked.append(RankedResult(
                result=result,
                relevance_score=relevance_scores[i],
                quality_score=quality_scores[i],
                recency_score=recency_scores[i],
            ))
        
        # Apply MMR for diversity if enabled
        if enable_diversity and len(ranked) > 1:
            ranked = self._apply_mmr(ranked, query)
        
        # Calculate final scores
        for r in ranked:
            r.final_score = (
                self.weights["relevance"] * r.relevance_score +
                self.weights["diversity"] * r.diversity_score +
                self.weights["recency"] * r.recency_score +
                self.weights["quality"] * r.quality_score
            )
            r.ranking_factors = {
                "relevance": r.relevance_score,
                "diversity": r.diversity_score,
                "recency": r.recency_score,
                "quality": r.quality_score,
            }
        
        # Sort by final score
        ranked.sort(key=lambda x: x.final_score, reverse=True)
        
        return ranked
    
    def _calculate_relevance(self, results: List[Any], query: str) -> List[float]:
        """Calculate relevance scores using simple TF-based approach"""
        query_terms = self._tokenize(query)
        scores = []
        
        for result in results:
            # Get text content from result
            text = self._extract_text(result).lower()
            text_terms = self._tokenize(text)
            
            if not text_terms:
                scores.append(0.0)
                continue
            
            # Calculate term frequency overlap
            text_counter = Counter(text_terms)
            query_counter = Counter(query_terms)
            
            # Compute cosine similarity approximation
            score = 0.0
            for term in query_terms:
                if term in text_counter:
                    # TF weighting
                    tf = 1 + math.log(text_counter[term]) if text_counter[term] > 0 else 0
                    score += tf
            
            # Normalize
            score /= (len(query_terms) * math.log(len(text_terms) + 1) + 1)
            scores.append(min(score, 1.0))
        
        return scores
    
    def _calculate_quality(self, results: List[Any]) -> List[float]:
        """Calculate quality scores based on heuristics"""
        scores = []
        
        for result in results:
            score = 0.5  # Base score
            text = self._extract_text(result)
            
            # URL quality indicators
            url = self._extract_url(result)
            if url:
                # Prefer .edu, .gov domains
                if ".edu" in url or ".gov" in url:
                    score += 0.2
                # Prefer HTTPS
                if url.startswith("https://"):
                    score += 0.1
                # Penalize very long URLs (often spam)
                if len(url) > 200:
                    score -= 0.1
            
            # Content length (not too short, not too long)
            text_len = len(text)
            if 100 <= text_len <= 1000:
                score += 0.1
            elif text_len < 50:
                score -= 0.1
            
            # Content quality indicators
            if text:
                # Penalize excessive capitalization
                caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
                if caps_ratio > 0.3:
                    score -= 0.1
                
                # Penalize excessive punctuation
                punct_ratio = sum(1 for c in text if c in "!?.:;") / max(len(text), 1)
                if punct_ratio > 0.1:
                    score -= 0.05
            
            scores.append(max(0.0, min(1.0, score)))
        
        return scores
    
    def _calculate_recency(self, results: List[Any]) -> List[float]:
        """Calculate recency scores based on timestamps"""
        scores = []
        now = datetime.now()
        
        for result in results:
            timestamp = self._extract_timestamp(result)
            
            if timestamp is None:
                scores.append(0.5)  # Neutral score for unknown
                continue
            
            age = now - timestamp
            
            # Exponential decay based on age
            if age < timedelta(hours=1):
                score = 1.0
            elif age < timedelta(days=1):
                score = 0.9
            elif age < timedelta(days=7):
                score = 0.7
            elif age < timedelta(days=30):
                score = 0.5
            elif age < timedelta(days=365):
                score = 0.3
            else:
                score = 0.1
            
            scores.append(score)
        
        return scores
    
    def _apply_mmr(self, ranked: List[RankedResult], query: str, lambda_param: float = 0.5) -> List[RankedResult]:
        """
        Apply Maximal Marginal Relevance for diversity
        
        MMR balances relevance with diversity by selecting items
        that are both relevant and different from already selected items.
        """
        if not ranked:
            return ranked
        
        selected = []
        remaining = ranked.copy()
        
        # Select first item based on relevance only
        best_idx = max(range(len(remaining)), key=lambda i: remaining[i].relevance_score)
        selected.append(remaining.pop(best_idx))
        
        # Select remaining items using MMR
        while remaining and len(selected) < len(ranked):
            best_mmr_score = -float("inf")
            best_idx = -1
            
            for i, candidate in enumerate(remaining):
                # Calculate max similarity to selected items
                max_sim = 0.0
                for sel in selected:
                    sim = self._similarity(candidate, sel, query)
                    max_sim = max(max_sim, sim)
                
                # MMR score: lambda * Relevance - (1-lambda) * max_sim
                mmr_score = (
                    lambda_param * candidate.relevance_score -
                    (1 - lambda_param) * max_sim
                )
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = i
            
            if best_idx >= 0:
                selected_item = remaining.pop(best_idx)
                selected_item.diversity_score = best_mmr_score
                selected.append(selected_item)
        
        return selected
    
    def _similarity(self, r1: RankedResult, r2: RankedResult, query: str) -> float:
        """Calculate similarity between two results"""
        text1 = self._extract_text(r1.result)
        text2 = self._extract_text(r2.result)
        
        # Simple Jaccard similarity on terms
        terms1 = set(self._tokenize(text1))
        terms2 = set(self._tokenize(text2))
        
        if not terms1 or not terms2:
            return 0.0
        
        intersection = terms1 & terms2
        union = terms1 | terms2
        
        return len(intersection) / len(union)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        return [w for w in words if w not in stop_words]
    
    def _extract_text(self, result: Any) -> str:
        """Extract text content from result object"""
        if hasattr(result, 'title') and hasattr(result, 'snippet'):
            return f"{result.title} {result.snippet}"
        elif hasattr(result, 'title'):
            return result.title
        elif hasattr(result, 'snippet'):
            return result.snippet
        elif hasattr(result, 'abstract'):
            return result.abstract
        elif isinstance(result, dict):
            return result.get("title", "") + " " + result.get("snippet", "")
        else:
            return str(result)
    
    def _extract_url(self, result: Any) -> Optional[str]:
        """Extract URL from result object"""
        if hasattr(result, 'url'):
            return result.url
        elif isinstance(result, dict):
            return result.get("url")
        return None
    
    def _extract_timestamp(self, result: Any) -> Optional[datetime]:
        """Extract timestamp from result object"""
        if hasattr(result, 'timestamp'):
            return result.timestamp
        elif hasattr(result, 'published_at'):
            return result.published_at
        elif isinstance(result, dict):
            ts = result.get("timestamp") or result.get("published_at")
            if isinstance(ts, str):
                try:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except:
                    pass
            return ts
        return None


class ResultFilter:
    """
    Result filtering utilities
    """
    
    @staticmethod
    def remove_duplicates(
        results: List[Any],
        similarity_threshold: float = 0.85
    ) -> List[Any]:
        """
        Remove duplicate results based on content similarity
        
        Args:
            results: List of results
            similarity_threshold: Threshold for considering items duplicates
            
        Returns:
            Filtered list without duplicates
        """
        if not results:
            return results
        
        filtered = []
        
        for result in results:
            is_duplicate = False
            
            for existing in filtered:
                sim = ResultFilter._content_similarity(result, existing)
                if sim >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(result)
        
        return filtered
    
    @staticmethod
    def filter_by_domain(
        results: List[Any],
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[Any]:
        """
        Filter results by domain
        
        Args:
            results: List of results
            include_domains: Only include these domains (if specified)
            exclude_domains: Exclude these domains
            
        Returns:
            Filtered results
        """
        filtered = []
        
        for result in results:
            url = ResultFilter._get_url(result)
            if not url:
                continue
            
            domain = ResultFilter._extract_domain(url)
            
            # Check include list
            if include_domains:
                if not any(d in domain for d in include_domains):
                    continue
            
            # Check exclude list
            if exclude_domains:
                if any(d in domain for d in exclude_domains):
                    continue
            
            filtered.append(result)
        
        return filtered
    
    @staticmethod
    def filter_by_date(
        results: List[Any],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[Any]:
        """
        Filter results by date range
        
        Args:
            results: List of results
            since: Only include results after this date
            until: Only include results before this date
            
        Returns:
            Filtered results
        """
        filtered = []
        
        for result in results:
            timestamp = ResultFilter._get_timestamp(result)
            
            if timestamp is None:
                # Include results without timestamps unless strict filtering
                filtered.append(result)
                continue
            
            if since and timestamp < since:
                continue
            if until and timestamp > until:
                continue
            
            filtered.append(result)
        
        return filtered
    
    @staticmethod
    def filter_by_content_length(
        results: List[Any],
        min_length: int = 0,
        max_length: Optional[int] = None,
    ) -> List[Any]:
        """
        Filter results by content length
        
        Args:
            results: List of results
            min_length: Minimum content length
            max_length: Maximum content length
            
        Returns:
            Filtered results
        """
        filtered = []
        
        for result in results:
            text = ResultFilter._get_text(result)
            length = len(text)
            
            if length < min_length:
                continue
            if max_length and length > max_length:
                continue
            
            filtered.append(result)
        
        return filtered
    
    @staticmethod
    def _content_similarity(r1: Any, r2: Any) -> float:
        """Calculate content similarity between two results"""
        text1 = ResultFilter._get_text(r1).lower()
        text2 = ResultFilter._get_text(r2).lower()
        
        # Use simple Jaccard similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    @staticmethod
    def _get_url(result: Any) -> Optional[str]:
        """Extract URL from result"""
        if hasattr(result, 'url'):
            return result.url
        elif isinstance(result, dict):
            return result.get("url")
        return None
    
    @staticmethod
    def _get_text(result: Any) -> str:
        """Extract text from result"""
        if hasattr(result, 'title') and hasattr(result, 'snippet'):
            return f"{result.title} {result.snippet}"
        elif hasattr(result, 'title'):
            return result.title
        elif hasattr(result, 'snippet'):
            return result.snippet
        elif isinstance(result, dict):
            return result.get("title", "") + " " + result.get("snippet", "")
        return str(result)
    
    @staticmethod
    def _get_timestamp(result: Any) -> Optional[datetime]:
        """Extract timestamp from result"""
        if hasattr(result, 'timestamp'):
            return result.timestamp
        elif hasattr(result, 'published_at'):
            return result.published_at
        elif isinstance(result, dict):
            ts = result.get("timestamp") or result.get("published_at")
            if isinstance(ts, str):
                try:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except:
                    pass
            return ts
        return None
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL"""
        # Simple domain extraction
        url = url.replace("https://", "").replace("http://", "")
        return url.split("/")[0].lower()


class ResultAggregator:
    """
    Aggregate and merge results from multiple providers
    """
    
    @staticmethod
    def merge_results(
        provider_results: Dict[str, List[Any]],
        max_results: int = 10,
        deduplicate: bool = True,
        ranker: Optional[ResultRanker] = None,
    ) -> List[Any]:
        """
        Merge results from multiple providers
        
        Args:
            provider_results: Dict mapping provider name to results
            max_results: Maximum number of results to return
            deduplicate: Whether to remove duplicates
            ranker: Optional ranker to apply
            
        Returns:
            Merged and ranked results
        """
        # Flatten results with provider info
        all_results = []
        for provider, results in provider_results.items():
            for result in results:
                # Tag result with provider
                if hasattr(result, 'metadata') and result.metadata is not None:
                    result.metadata["_provider"] = provider
                else:
                    result.metadata = {"_provider": provider}
                all_results.append(result)
        
        # Deduplicate if requested
        if deduplicate:
            all_results = ResultFilter.remove_duplicates(all_results)
        
        # Rank if ranker provided
        if ranker and all_results:
            # Get a representative query (from first result metadata if available)
            query = ""
            if all_results and hasattr(all_results[0], 'metadata'):
                query = all_results[0].metadata.get('_query', '')
            
            ranked = ranker.rank(all_results, query)
            all_results = [r.result for r in ranked]
        
        # Return top results
        return all_results[:max_results]
    
    @staticmethod
    def round_robin(
        provider_results: Dict[str, List[Any]],
        max_results: int = 10,
    ) -> List[Any]:
        """
        Merge results using round-robin from each provider
        
        This ensures diversity by giving each provider equal representation.
        """
        all_results = []
        providers = list(provider_results.keys())
        indices = {p: 0 for p in providers}
        
        while len(all_results) < max_results:
            added = False
            for provider in providers:
                results = provider_results[provider]
                idx = indices[provider]
                
                if idx < len(results):
                    all_results.append(results[idx])
                    indices[provider] = idx + 1
                    added = True
                    
                    if len(all_results) >= max_results:
                        break
            
            if not added:
                break
        
        return all_results
