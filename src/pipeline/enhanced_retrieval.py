#!/usr/bin/env python3
"""
ENHANCED RETRIEVAL — Background use of temporal + Hebbian data
Part of localize_it: Personal AI Sovereignty

Automatically enhances retrieval using enriched capture data.
No new commands — existing queries get smarter.
"""

import sys
sys.path.insert(0, '/home/kinch/Projects/localize_it/src')

from temporal.classifier import TemporalClassifier, prioritize_by_temporal
from memory.associations import HebbianGraph
import json
from pathlib import Path
from typing import List, Dict

class EnhancedRetriever:
    """Smart retrieval using temporal + Hebbian, transparent to user."""
    
    def __init__(self):
        self.temporal = TemporalClassifier()
        self.hebbian = HebbianGraph()
        
    def search(self, query: str, prefer_present: bool = True) -> List[Dict]:
        """
        Search captures with automatic enhancement.
        
        If prefer_present=True (default), prioritizes 'present' temporal state.
        Uses Hebbian associations to expand query implicitly.
        
        No new commands — just smarter results.
        """
        # 1. Load all captures
        captures = self._load_all_captures()
        if not captures:
            return []
        
        # 2. Get Hebbian expansion (implicit query broadening)
        related_concepts = self.hebbian.related_to(query, depth=1, min_weight=1.0)
        concept_list = [c[0] for c in related_concepts[:5]]  # Top 5 related
        
        # 3. Score captures by relevance (TF-IDF + Hebbian)
        scored = []
        for capture in captures:
            content = capture.get('content', capture.get('raw_input', ''))
            base_score = self._text_similarity(query, content)
            
            # Hebbian boost if content mentions related concepts
            hebbian_boost = 0
            for concept in concept_list:
                if concept in content.lower():
                    hebbian_boost += 0.1
            
            # Temporal boost if preferred state
            temporal_boost = 0
            temporal_state = capture.get('temporal', {}).get('state', 'unknown')
            temporal_conf = capture.get('temporal', {}).get('confidence', 0)
            
            if prefer_present and temporal_state == 'present':
                temporal_boost = temporal_conf * 0.2  # Up to 0.2 boost
            
            final_score = min(1.0, base_score + hebbian_boost + temporal_boost)
            
            scored.append({
                'capture': capture,
                'score': final_score,
                'temporal_state': temporal_state,
                'hebbian_boost': hebbian_boost > 0,
                'temporal_boost': temporal_boost > 0
            })
        
        # 4. Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        
        # 5. Return enhanced results (with metadata for transparency)
        return scored[:10]  # Top 10
    
    def get_present_work(self) -> List[Dict]:
        """
        Get all captures tagged as 'present' — what am I actively building?
        
        Uses temporal auto-tags. No manual tagging required.
        """
        captures = self._load_all_captures()
        
        present_captures = [
            c for c in captures 
            if c.get('temporal', {}).get('state') == 'present' 
            and c.get('temporal', {}).get('confidence', 0) >= 0.5
        ]
        
        # Sort by temporal confidence
        present_captures.sort(
            key=lambda x: x.get('temporal', {}).get('confidence', 0),
            reverse=True
        )
        
        return present_captures[:15]  # Top 15 active work items
    
    def get_related_to_topic(self, topic: str, depth: int = 1) -> List[Dict]:
        """
        Get captures related to a topic via Hebbian associations.
        
        Example: get_related_to_topic("docker") returns captures about 
        docker, containers, compose, yaml, etc.
        """
        # Get related concepts from graph
        related = self.hebbian.related_to(topic, depth=depth, min_weight=1.0)
        
        captures = self._load_all_captures()
        
        # Find captures mentioning topic or related concepts
        related_captures = []
        related_terms = [topic] + [c[0] for c in related]
        
        for capture in captures:
            content = capture.get('content', capture.get('raw_input', '')).lower()
            for term in related_terms:
                if term in content:
                    related_captures.append({
                        'capture': capture,
                        'matched_term': term,
                        'weight': next((c[1] for c in related if c[0] == term), 1.0)
                    })
                    break
        
        # Sort by association weight
        related_captures.sort(key=lambda x: x['weight'], reverse=True)
        return related_captures[:10]
    
    def _load_all_captures(self) -> List[Dict]:
        """Load all captures from storage."""
        import glob
        captures = []
        
        # Load from localize log
        log_file = Path('/home/kinch/Projects/localize_it/data/localize/entries.jsonl')
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            captures.append(json.loads(line))
                        except:
                            continue
        
        return captures
    
    def _text_similarity(self, query: str, text: str) -> float:
        """Simple text similarity score (0-1)."""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        if not query_words:
            return 0
        
        overlap = query_words & text_words
        return len(overlap) / len(query_words)


# Simple CLI for testing
if __name__ == '__main__':
    retriever = EnhancedRetriever()
    
    print("Enhanced Retrieval Test")
    print("=" * 60)
    
    # Test 1: Present work
    print("\n📌 What am I actively building? (Temporal = 'present')")
    present = retriever.get_present_work()
    for i, cap in enumerate(present[:5], 1):
        content = cap.get('content', cap.get('raw_input', ''))[:60]
        conf = cap.get('temporal', {}).get('confidence', 0)
        print(f"  {i}. {content}... (conf: {conf:.2f})")
    
    # Test 2: Related to topic
    print("\n🔗 Related to 'kennel':")
    related = retriever.get_related_to_topic("kennel", depth=1)
    for i, item in enumerate(related[:5], 1):
        cap = item['capture']
        term = item['matched_term']
        content = cap.get('content', cap.get('raw_input', ''))[:60]
        print(f"  {i}. [{term}] {content}...")
