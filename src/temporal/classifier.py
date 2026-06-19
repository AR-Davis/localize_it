#!/usr/bin/env python3
"""
TEMPORAL CLASSIFIER — Auto-tag captures with past/present/future orientation

Heuristic-based classification using keyword detection.
Part of localize_it: Personal AI Sovereignty
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class TemporalClassification:
    """Result of temporal classification."""
    state: str  # 'past', 'present', 'future', 'unknown'
    confidence: float  # 0.0-1.0
    method: str  # 'keyword_detection', 'explicit_marker', 'context_inference'
    matched_keywords: List[str]


class TemporalClassifier:
    """Classify captures by temporal state."""
    
    # Keyword patterns for temporal classification
    PAST_KEYWORDS = {
        'strong': ['complete', 'done', 'finished', 'shipped', 'deployed', 'archived', 
                   'closed', 'resolved', 'fixed', 'learned', 'lesson', 'retrospective'],
        'medium': ['was', 'were', 'had', 'previous', 'last', 'yesterday', 'ago'],
        'weak': ['before', 'earlier', 'prior']
    }
    
    PRESENT_KEYWORDS = {
        'strong': ['active', 'building', 'current', 'in_progress', 'implementing',
                   'working on', 'developing', 'now', 'currently', 'today'],
        'medium': ['is', 'are', 'doing', 'creating', 'writing'],
        'weak': ['ongoing', 'progress', 'underway']
    }
    
    FUTURE_KEYWORDS = {
        'strong': ['plan', 'future', 'upcoming', 'next', 'after', 'when', 'will',
                   'todo', 'up next', 'roadmap', 'someday', 'eventually'],
        'medium': ['should', 'could', 'might', 'consider', 'explore', 'investigate'],
        'weak': ['maybe', 'possibly', 'thinking about']
    }
    
    # Explicit markers override keyword detection
    EXPLICIT_MARKERS = {
        r'\[PAST\]': 'past',
        r'\[PRESENT\]': 'present', 
        r'\[FUTURE\]': 'future',
        r'\[DONE\]': 'past',
        r'\[WIP\]': 'present',
        r'\[TODO\]': 'future',
    }
    
    def __init__(self, confidence_threshold: float = 0.3):
        self.confidence_threshold = confidence_threshold
    
    def classify(self, content: str) -> TemporalClassification:
        """
        Classify content by temporal state.
        
        Args:
            content: Text content to classify
            
        Returns:
            TemporalClassification with state, confidence, method
        """
        content_lower = content.lower()
        
        # Check for explicit markers first
        for pattern, state in self.EXPLICIT_MARKERS.items():
            if re.search(pattern, content, re.IGNORECASE):
                return TemporalClassification(
                    state=state,
                    confidence=0.95,
                    method='explicit_marker',
                    matched_keywords=[pattern]
                )
        
        # Score each temporal state
        past_score = self._score_keywords(content_lower, self.PAST_KEYWORDS)
        present_score = self._score_keywords(content_lower, self.PRESENT_KEYWORDS)
        future_score = self._score_keywords(content_lower, self.FUTURE_KEYWORDS)
        
        # Determine dominant state
        scores = {'past': past_score, 'present': present_score, 'future': future_score}
        dominant_state = max(scores, key=scores.get)
        dominant_score = scores[dominant_state]
        
        # Calculate confidence based on score differential
        total_score = sum(scores.values())
        if total_score == 0:
            return TemporalClassification(
                state='unknown',
                confidence=0.0,
                method='keyword_detection',
                matched_keywords=[]
            )
        
        confidence = dominant_score / total_score
        matched = self._get_matched_keywords(content_lower, getattr(self, f'{dominant_state.upper()}_KEYWORDS'))
        
        return TemporalClassification(
            state=dominant_state,
            confidence=confidence,
            method='keyword_detection',
            matched_keywords=matched
        )
    
    def _score_keywords(self, content: str, keyword_sets: Dict[str, List[str]]) -> float:
        """Score content against keyword sets."""
        score = 0.0
        for strength, keywords in keyword_sets.items():
            weight = {'strong': 3.0, 'medium': 2.0, 'weak': 1.0}[strength]
            for keyword in keywords:
                if keyword in content:
                    score += weight
        return score
    
    def _get_matched_keywords(self, content: str, keyword_sets: Dict[str, List[str]]) -> List[str]:
        """Return list of matched keywords."""
        matched = []
        for keywords in keyword_sets.values():
            for keyword in keywords:
                if keyword in content:
                    matched.append(keyword)
        return matched


# Convenience functions for common operations

def classify_capture(content: str, classifier: Optional[TemporalClassifier] = None) -> TemporalClassification:
    """Classify a single capture by temporal state."""
    if classifier is None:
        classifier = TemporalClassifier()
    return classifier.classify(content)


def query_by_temporal(captures: List[Dict], temporal_state: str, 
                      min_confidence: float = 0.5) -> List[Dict]:
    """
    Filter captures by temporal state.
    
    Args:
        captures: List of capture dictionaries with 'content' field
        temporal_state: 'past', 'present', 'future', or 'unknown'
        min_confidence: Minimum confidence threshold
        
    Returns:
        Filtered list of captures matching temporal state
    """
    classifier = TemporalClassifier()
    results = []
    
    for capture in captures:
        content = capture.get('content', '')
        classification = classifier.classify(content)
        
        if classification.state == temporal_state and classification.confidence >= min_confidence:
            # Enrich capture with temporal metadata
            capture_with_temporal = capture.copy()
            capture_with_temporal['temporal'] = {
                'state': classification.state,
                'confidence': classification.confidence,
                'method': classification.method,
                'keywords': classification.matched_keywords
            }
            results.append(capture_with_temporal)
    
    # Sort by confidence descending
    results.sort(key=lambda x: x['temporal']['confidence'], reverse=True)
    return results


def prioritize_by_temporal(captures: List[Dict], preferred_state: str = 'present') -> List[Dict]:
    """
    Sort captures by temporal relevance (preferred state first).
    
    Args:
        captures: List of capture dictionaries
        preferred_state: Temporal state to prioritize ('past', 'present', 'future')
        
    Returns:
        Sorted list with preferred temporal state first
    """
    classifier = TemporalClassifier()
    
    # Enrich all captures with temporal data
    enriched = []
    for capture in captures:
        content = capture.get('content', '')
        classification = classifier.classify(content)
        
        capture_copy = capture.copy()
        capture_copy['temporal'] = {
            'state': classification.state,
            'confidence': classification.confidence,
            'method': classification.method,
            'keywords': classification.matched_keywords
        }
        enriched.append(capture_copy)
    
    # Sort: preferred state first, then by confidence
    enriched.sort(key=lambda x: (
        0 if x['temporal']['state'] == preferred_state else 1,
        -x['temporal']['confidence']
    ))
    
    return enriched


if __name__ == '__main__':
    # Test cases
    test_cases = [
        ("Complete the auth module", "past"),
        ("Building a new trading bot", "present"),
        ("Plan to refactor next week", "future"),
        ("What should we do?", "future"),
        ("Currently working on the parser", "present"),
        ("Lesson learned: always validate input", "past"),
    ]
    
    classifier = TemporalClassifier()
    
    print("Temporal Classification Tests")
    print("=" * 60)
    
    for content, expected in test_cases:
        result = classifier.classify(content)
        status = "✓" if result.state == expected else "✗"
        print(f"{status} '{content}'")
        print(f"   → {result.state} (conf: {result.confidence:.2f}, {result.method})")
        print(f"   Matched: {', '.join(result.matched_keywords)}")
        print()
