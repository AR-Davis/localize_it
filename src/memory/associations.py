#!/usr/bin/env python3
"""
HEBBIAN ASSOCIATION GRAPH — Concept co-occurrence tracking
Part of localize_it: Personal AI Sovereignty

"Cells that fire together, wire together"
Complements TF-IDF by finding implicit connections between concepts.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict
import math


@dataclass
class Association:
    """Single association between two concepts."""
    concept_a: str
    concept_b: str
    weight: float
    first_seen: str
    last_seen: str
    contexts: List[str]
    emotional_weight: float = 1.0  # Optional: weight by emotional intensity


class HebbianGraph:
    """
    Hebbian learning graph for concept associations.
    
    Tracks co-occurrence of concepts across captures and enables
    associative retrieval alongside TF-IDF similarity search.
    """
    
    def __init__(self, storage_path: str = "data/memory/hebbian"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Graph: {(concept_a, concept_b): Association}
        self.graph: Dict[Tuple[str, str], Association] = {}
        
        # Concept index: {concept: [related_concepts]}
        self.concept_index: Dict[str, Set[str]] = defaultdict(set)
        
        self.load()
    
    def _canonicalize(self, concept_a: str, concept_b: str) -> Tuple[str, str]:
        """Canonicalize concept pair (alphabetical order)."""
        return tuple(sorted([concept_a.lower().strip(), concept_b.lower().strip()]))
    
    def _extract_concepts(self, text: str) -> List[str]:
        """
        Extract key concepts from text.
        
        Strategy:
        1. Named entities (capitalized phrases)
        2. Technical terms (code, APIs, tools)
        3. Key nouns (filtered)
        """
        concepts = []
        
        # Named entities (capitalized)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        concepts.extend([e.lower() for e in entities])
        
        # Technical terms (camelCase, snake_case, hyphenated)
        tech_patterns = [
            r'\b[a-z]+_[a-z_]+\b',  # snake_case
            r'\b[a-z]+[A-Z][a-zA-Z]+\b',  # camelCase/PascalCase
            r'\b[a-z]+-[a-z-]+\b',  # hyphenated
            r'\b\w+\.\w+\b',  # module.function
        ]
        for pattern in tech_patterns:
            matches = re.findall(pattern, text)
            concepts.extend([m.lower() for m in matches])
        
        # Key nouns (common technical terms)
        tech_nouns = ['docker', 'python', 'javascript', 'api', 'database', 'server',
                     'client', 'function', 'class', 'method', 'variable', 'config',
                     'json', 'yaml', 'xml', 'http', 'https', 'ssh', 'git',
                     'localize', 'kennel', 'shepherd', 'temporal', 'shadow',
                     'router', 'memory', 'pattern', 'framework', 'capture']
        
        for noun in tech_nouns:
            if noun in text.lower():
                concepts.append(noun)
        
        # Remove duplicates and short terms
        concepts = list(set(c for c in concepts if len(c) > 2))
        
        return concepts
    
    def reinforce(self, concepts: List[str], context: str = "", 
                  emotional_weight: float = 1.0, timestamp: str = None) -> None:
        """
        Strengthen associations between co-occurring concepts.
        
        Args:
            concepts: List of concepts that co-occurred
            context: Where/when this co-occurrence happened
            emotional_weight: Optional emotional intensity (1.0 = neutral)
            timestamp: ISO timestamp (default: now)
        """
        from datetime import datetime
        timestamp = timestamp or datetime.now().isoformat()
        
        # Generate all pairs
        from itertools import combinations
        for concept_a, concept_b in combinations(set(concepts), 2):
            pair = self._canonicalize(concept_a, concept_b)
            
            if pair in self.graph:
                # Strengthen existing association
                assoc = self.graph[pair]
                assoc.weight += emotional_weight
                assoc.last_seen = timestamp
                if context and context not in assoc.contexts:
                    assoc.contexts.append(context)
                    # Keep only last 10 contexts
                    assoc.contexts = assoc.contexts[-10:]
            else:
                # Create new association
                self.graph[pair] = Association(
                    concept_a=pair[0],
                    concept_b=pair[1],
                    weight=emotional_weight,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    contexts=[context] if context else [],
                    emotional_weight=emotional_weight
                )
            
            # Update concept index
            self.concept_index[pair[0]].add(pair[1])
            self.concept_index[pair[1]].add(pair[0])
    
    def reinforce_from_text(self, text: str, context: str = "", 
                           emotional_weight: float = 1.0) -> None:
        """
        Extract concepts from text and reinforce associations.
        
        Args:
            text: Source text to extract concepts from
            context: Where this text came from
            emotional_weight: Emotional intensity of this capture
        """
        concepts = self._extract_concepts(text)
        if len(concepts) >= 2:
            self.reinforce(concepts, context, emotional_weight)
    
    def related_to(self, query: str, depth: int = 1, min_weight: float = 1.0) -> List[Tuple[str, float]]:
        """
        Find concepts related to query via association graph.
        
        Args:
            query: Concept to find relations for
            depth: How many hops to traverse (1 = direct neighbors)
            min_weight: Minimum association weight to include
            
        Returns:
            List of (concept, strength) tuples, sorted by strength
        """
        query = query.lower().strip()
        related = defaultdict(float)
        
        # Direct neighbors (depth 1)
        for neighbor in self.concept_index.get(query, set()):
            pair = self._canonicalize(query, neighbor)
            if pair in self.graph:
                weight = self.graph[pair].weight
                if weight >= min_weight:
                    related[neighbor] = max(related[neighbor], weight)
        
        # Indirect neighbors (depth 2+)
        if depth > 1:
            current_depth = set(self.concept_index.get(query, set()))
            visited = {query} | current_depth
            
            for d in range(2, depth + 1):
                next_depth = set()
                for concept in current_depth:
                    for neighbor in self.concept_index.get(concept, set()):
                        if neighbor not in visited:
                            # Weight decays with distance
                            decay = 0.5 ** (d - 1)
                            pair = self._canonicalize(concept, neighbor)
                            if pair in self.graph:
                                weight = self.graph[pair].weight * decay
                                if weight >= min_weight:
                                    related[neighbor] = max(related[neighbor], weight)
                            next_depth.add(neighbor)
                            visited.add(neighbor)
                current_depth = next_depth
        
        # Sort by strength
        return sorted(related.items(), key=lambda x: x[1], reverse=True)
    
    def suggest_context(self, query: str, top_n: int = 5) -> Dict[str, List[str]]:
        """
        Suggest related concepts and contexts for a query.
        
        Args:
            query: Concept to find context for
            top_n: Number of suggestions to return
            
        Returns:
            Dict with 'primary' (direct) and 'secondary' (indirect) concepts
        """
        query = query.lower().strip()
        
        # Direct associations
        primary = self.related_to(query, depth=1, min_weight=2.0)[:top_n]
        
        # Indirect associations
        secondary = self.related_to(query, depth=2, min_weight=1.0)[:top_n]
        
        # Gather contexts
        contexts = []
        for concept, _ in primary:
            pair = self._canonicalize(query, concept)
            if pair in self.graph:
                contexts.extend(self.graph[pair].contexts)
        
        return {
            'primary': [c[0] for c in primary],
            'secondary': [c[0] for c in secondary],
            'contexts': list(set(contexts))[:top_n]
        }
    
    def walk_from(self, start_concept: str, depth: int = 2, 
                  min_weight: float = 1.0) -> List[str]:
        """
        Walk the association graph from a starting concept.
        
        Args:
            start_concept: Concept to start walking from
            depth: How many hops to traverse
            min_weight: Minimum weight to follow edge
            
        Returns:
            List of all concepts reachable within depth
        """
        related = self.related_to(start_concept, depth=depth, min_weight=min_weight)
        return [concept for concept, _ in related]
    
    def get_path(self, concept_a: str, concept_b: str, 
                 max_depth: int = 3) -> Optional[List[str]]:
        """
        Find path between two concepts via BFS.
        
        Args:
            concept_a: Starting concept
            concept_b: Target concept
            max_depth: Maximum path length
            
        Returns:
            Path as list of concepts, or None if no path found
        """
        concept_a = concept_a.lower().strip()
        concept_b = concept_b.lower().strip()
        
        if concept_a == concept_b:
            return [concept_a]
        
        # BFS
        from collections import deque
        queue = deque([(concept_a, [concept_a])])
        visited = {concept_a}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            for neighbor in self.concept_index.get(current, set()):
                if neighbor == concept_b:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def get_stats(self) -> Dict:
        """Get graph statistics."""
        if not self.graph:
            return {'nodes': 0, 'edges': 0, 'avg_weight': 0}
        
        concepts = set()
        total_weight = 0
        
        for pair, assoc in self.graph.items():
            concepts.add(pair[0])
            concepts.add(pair[1])
            total_weight += assoc.weight
        
        return {
            'nodes': len(concepts),
            'edges': len(self.graph),
            'avg_weight': total_weight / len(self.graph) if self.graph else 0,
            'top_concepts': sorted(
                [(c, len(self.concept_index[c])) for c in concepts],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def save(self) -> None:
        """Save graph to disk."""
        # Save associations
        associations_data = [
            {
                'concept_a': assoc.concept_a,
                'concept_b': assoc.concept_b,
                'weight': assoc.weight,
                'first_seen': assoc.first_seen,
                'last_seen': assoc.last_seen,
                'contexts': assoc.contexts,
                'emotional_weight': assoc.emotional_weight
            }
            for assoc in self.graph.values()
        ]
        
        with open(self.storage_path / 'associations.json', 'w') as f:
            json.dump(associations_data, f, indent=2)
        
        # Save stats
        with open(self.storage_path / 'stats.json', 'w') as f:
            json.dump(self.get_stats(), f, indent=2)
    
    def load(self) -> None:
        """Load graph from disk."""
        associations_file = self.storage_path / 'associations.json'
        
        if not associations_file.exists():
            return
        
        with open(associations_file, 'r') as f:
            associations_data = json.load(f)
        
        for data in associations_data:
            pair = self._canonicalize(data['concept_a'], data['concept_b'])
            self.graph[pair] = Association(
                concept_a=data['concept_a'],
                concept_b=data['concept_b'],
                weight=data['weight'],
                first_seen=data['first_seen'],
                last_seen=data['last_seen'],
                contexts=data.get('contexts', []),
                emotional_weight=data.get('emotional_weight', 1.0)
            )
            
            # Rebuild concept index
            self.concept_index[pair[0]].add(pair[1])
            self.concept_index[pair[1]].add(pair[0])


def hybrid_retrieve(graph: HebbianGraph, tfidf_results: List[Dict], 
                   query: str, tfidf_weight: float = 0.7) -> List[Dict]:
    """
    Combine TF-IDF similarity with association graph for hybrid retrieval.
    
    Args:
        graph: Hebbian association graph
        tfidf_results: Results from TF-IDF similarity search
        query: Original query
        tfidf_weight: Weight for TF-IDF vs associations (0.7 = 70% TF-IDF)
        
    Returns:
        Re-ranked results combining both signals
    """
    # Get associations for query
    assoc_concepts = graph.related_to(query, depth=2, min_weight=1.0)
    assoc_dict = {c: w for c, w in assoc_concepts}
    
    # Score each TF-IDF result
    scored_results = []
    for result in tfidf_results:
        tfidf_score = result.get('score', 0.5)
        
        # Check if result content mentions associated concepts
        content = result.get('content', '').lower()
        assoc_score = 0
        for concept, weight in assoc_dict.items():
            if concept in content:
                assoc_score += weight * 0.1  # Normalize
        
        # Combine scores
        combined = (tfidf_score * tfidf_weight) + (assoc_score * (1 - tfidf_weight))
        
        scored_results.append({
            **result,
            'hybrid_score': combined,
            'tfidf_score': tfidf_score,
            'assoc_score': assoc_score
        })
    
    # Sort by hybrid score
    scored_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
    
    return scored_results


# Example usage
if __name__ == '__main__':
    graph = HebbianGraph()
    
    # Reinforce from captures
    captures = [
        "Working on docker compose yaml config for the web service",
        "Dockerfile needs to be optimized with multi-stage builds",
        "Kubernetes deployment using the same container image",
        "Python script to automate docker image building",
    ]
    
    for i, capture in enumerate(captures):
        graph.reinforce_from_text(capture, context=f"capture_{i}")
    
    # Save
    graph.save()
    
    # Query
    print("Hebbian Association Graph Demo")
    print("=" * 60)
    
    print("\nRelated to 'docker':")
    related = graph.related_to('docker', depth=2, min_weight=1.0)
    for concept, strength in related:
        print(f"  {concept}: {strength:.1f}")
    
    print("\nSuggested context for 'docker':")
    suggestions = graph.suggest_context('docker', top_n=5)
    print(f"  Primary: {suggestions['primary']}")
    print(f"  Secondary: {suggestions['secondary']}")
    print(f"  Contexts: {suggestions['contexts']}")
    
    print("\nWalk from 'docker' (depth=2):")
    walk = graph.walk_from('docker', depth=2, min_weight=1.0)
    print(f"  {walk}")
    
    print("\nPath 'docker' → 'python':")
    path = graph.get_path('docker', 'python', max_depth=3)
    if path:
        print(f"  {' → '.join(path)}")
    else:
        print("  No path found")
    
    print("\nGraph stats:")
    stats = graph.get_stats()
    print(f"  Nodes: {stats['nodes']}")
    print(f"  Edges: {stats['edges']}")
    print(f"  Avg weight: {stats['avg_weight']:.2f}")
