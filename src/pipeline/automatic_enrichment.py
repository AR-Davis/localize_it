#!/usr/bin/env python3
"""
AUTOMATIC ENRICHMENT — Background processing for captures
Part of localize_it: Personal AI Sovereignty

Silently adds temporal tags and Hebbian associations to every capture.
No user action required. Works in background.
"""

import sys
sys.path.insert(0, '/home/kinch/Projects/localize_it/src')

from temporal.classifier import TemporalClassifier
from memory.associations import HebbianGraph
import json
from pathlib import Path
from datetime import datetime

class AutomaticEnricher:
    """Background enrichment: temporal + Hebbian, zero user effort."""
    
    def __init__(self):
        self.temporal = TemporalClassifier()
        self.hebbian = HebbianGraph()
        
    def enrich_capture(self, capture: dict) -> dict:
        """
        Enrich a capture with temporal and Hebbian metadata.
        Called automatically during capture pipeline.
        """
        content = capture.get('content', '')
        
        # 1. Temporal classification (background)
        temporal_result = self.temporal.classify(content)
        capture['temporal'] = {
            'state': temporal_result.state,
            'confidence': temporal_result.confidence,
            'keywords': temporal_result.matched_keywords,
            'auto_tagged': True
        }
        
        # 2. Hebbian association extraction (background)
        self.hebbian.reinforce_from_text(
            content,
            context=capture.get('id', 'capture'),
            emotional_weight=capture.get('importance', 1.0)
        )
        
        # 3. Suggest related concepts (for retrieval enhancement)
        related = self.hebbian.suggest_context(content[:50], top_n=3)
        capture['associations'] = {
            'primary_concepts': related.get('primary', []),
            'auto_extracted': True
        }
        
        return capture
    
    def batch_enrich_existing(self, corpus_path: str = None):
        """
        One-time batch processing of existing captures.
        Run once to backfill temporal + Hebbian for all history.
        """
        if corpus_path is None:
            corpus_path = '/home/kinch/Projects/localize_it/data/training/corpus-*.json'
        
        import glob
        
        total = 0
        for corpus_file in glob.glob(corpus_path):
            try:
                with open(corpus_file, 'r') as f:
                    data = json.load(f)
                
                examples = data.get('examples', [])
                for example in examples:
                    content = example.get('content', example.get('query', ''))
                    
                    # Temporal
                    temporal = self.temporal.classify(content)
                    example['temporal'] = {
                        'state': temporal.state,
                        'confidence': temporal.confidence,
                        'auto_tagged': True
                    }
                    
                    # Hebbian
                    self.hebbian.reinforce_from_text(content)
                    
                    total += 1
                
                # Save enriched version
                with open(corpus_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
            except Exception as e:
                print(f"Error processing {corpus_file}: {e}")
                continue
        
        # Save Hebbian graph
        self.hebbian.save()
        
        print(f"Batch enrichment complete: {total} captures processed")
        print(f"Temporal tags added: {total}")
        print(f"Hebbian associations: {len(self.hebbian.graph)} pairs")
        
        return total

if __name__ == '__main__':
    enricher = AutomaticEnricher()
    
    # Example: enrich a single capture
    test_capture = {
        'id': 'test-001',
        'content': 'Building the Hebbian integration for temporal pattern detection',
        'category': 'TECHNICAL',
        'importance': 0.9
    }
    
    enriched = enricher.enrich_capture(test_capture)
    print(json.dumps(enriched, indent=2))
