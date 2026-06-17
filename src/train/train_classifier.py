#!/usr/bin/env python3
"""
TRAIN_CLASSIFIER — Train query type and style classifiers from localize_it data
Part of LOCALIZE_IT: Personal AI Sovereignty

Trains:
1. Query type classifier (SOCIAL, LEARNING, TECHNICAL, JOB_HUNT, WAKE, etc.)
2. Style similarity model for retrieving relevant frameworks/contexts
"""

import json
import pickle
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
DATA_DIR = PROJECT_DIR / "data"
SHADOW_DIR = DATA_DIR / "shadow"
EXPLICIT_DIR = DATA_DIR / "explicit"
MODEL_DIR = PROJECT_DIR / "models"


def load_training_data() -> Tuple[List[str], List[str]]:
    """Load training examples from shadow classification and explicit captures."""
    texts = []
    labels = []
    
    # Load from shadow classification
    classification_file = SHADOW_DIR / "classification-2026-06-12.json"
    if classification_file.exists():
        with open(classification_file) as f:
            classification = json.load(f)
        
        for category, data in classification.get("categories", {}).items():
            for example in data.get("examples", [])[:50]:  # Limit per category
                texts.append(example.get("text", ""))
                labels.append(category)
    
    # Add pattern-based labels from patterns file
    patterns_file = SHADOW_DIR / "patterns" / "2026-06-12.json"
    if patterns_file.exists():
        with open(patterns_file) as f:
            patterns = json.load(f)
        
        # Wake requests
        for wake in patterns.get("patterns", {}).get("query_patterns", {}).get("wake_requests", [])[:30]:
            texts.append(wake.get("query", ""))
            labels.append("WAKE_REQUEST")
    
    # Add explicit captures as training examples
    # Frameworks -> TECHNICAL
    frameworks_file = EXPLICIT_DIR / "frameworks" / "frameworks.jsonl"
    if frameworks_file.exists():
        for line in frameworks_file.read_text().strip().split('\n'):
            if line:
                fw = json.loads(line)
                texts.append(fw.get("description", fw.get("raw_input", "")))
                labels.append("TECHNICAL")
    
    # Contexts -> PROJECT_SPECIFIC
    contexts_file = EXPLICIT_DIR / "contexts" / "contexts.jsonl"
    if contexts_file.exists():
        for line in contexts_file.read_text().strip().split('\n'):
            if line:
                ctx = json.loads(line)
                texts.append(ctx.get("description", ""))
                labels.append("PROJECT_SPECIFIC")
    
    # Learning examples -> LEARNING
    learning_file = EXPLICIT_DIR / "learning" / "learning-examples.jsonl"
    if learning_file.exists():
        for line in learning_file.read_text().strip().split('\n'):
            if line:
                example = json.loads(line)
                texts.append(example.get("text", ""))
                labels.append(example.get("category", "LEARNING"))
    
    return texts, labels


def train_query_classifier(texts: List[str], labels: List[str]) -> Pipeline:
    """Train a query type classifier."""
    # Filter out empty texts
    valid_pairs = [(t, l) for t, l in zip(texts, labels) if t.strip()]
    texts = [p[0] for p in valid_pairs]
    labels = [p[1] for p in valid_pairs]
    
    print(f"Training on {len(texts)} examples...")
    print(f"Categories: {set(labels)}")
    
    # Split for evaluation
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
    except ValueError:
        # Some classes have too few examples for stratification
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
    
    # Create pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words='english'
        )),
        ('classifier', MultinomialNB(alpha=0.1))
    ])
    
    # Train
    pipeline.fit(X_train, y_train)
    
    # Evaluate
    score = pipeline.score(X_test, y_test)
    print(f"\nAccuracy: {score:.3f}")
    
    # Detailed report
    y_pred = pipeline.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    return pipeline


def build_style_embeddings() -> Dict:
    """Build embedding index for style/framework retrieval."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    # Load explicit captures
    entries = []
    metadata = []
    
    # Load frameworks
    frameworks_file = EXPLICIT_DIR / "frameworks" / "frameworks.jsonl"
    if frameworks_file.exists():
        for line in frameworks_file.read_text().strip().split('\n'):
            if line:
                fw = json.loads(line)
                text = f"{fw.get('name', '')} {fw.get('description', '')}"
                entries.append(text)
                metadata.append({
                    'type': 'framework',
                    'name': fw.get('name'),
                    'source': 'frameworks.jsonl'
                })
    
    # Load contexts
    contexts_file = EXPLICIT_DIR / "contexts" / "contexts.jsonl"
    if contexts_file.exists():
        for line in contexts_file.read_text().strip().split('\n'):
            if line:
                ctx = json.loads(line)
                text = f"{ctx.get('project', '')} {ctx.get('description', '')}"
                entries.append(text)
                metadata.append({
                    'type': 'context',
                    'name': ctx.get('project'),
                    'source': 'contexts.jsonl'
                })
    
    # Build vectorizer
    vectorizer = TfidfVectorizer(max_features=1000)
    vectors = vectorizer.fit_transform(entries)
    
    return {
        'vectorizer': vectorizer,
        'vectors': vectors,
        'entries': entries,
        'metadata': metadata
    }


def save_models(query_classifier: Pipeline, style_index: Dict, output_dir: Path):
    """Save trained models to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save query classifier
    with open(output_dir / "query_classifier.pkl", 'wb') as f:
        pickle.dump(query_classifier, f)
    
    # Save style index
    with open(output_dir / "style_index.pkl", 'wb') as f:
        pickle.dump(style_index, f)
    
    # Save metadata
    metadata = {
        'trained_at': datetime.now().isoformat(),
        'version': '1.0',
        'query_categories': list(query_classifier.classes_),
        'explicit_entries': len(style_index['entries'])
    }
    with open(output_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✓ Models saved to {output_dir}")
    print(f"  - query_classifier.pkl")
    print(f"  - style_index.pkl")
    print(f"  - metadata.json")


def main():
    parser = argparse.ArgumentParser(description="Train localize_it classifiers")
    parser.add_argument("--output", "-o", type=Path, default=MODEL_DIR,
                       help="Output directory for trained models")
    parser.add_argument("--eval-only", action="store_true",
                       help="Only evaluate, don't save")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("LOCALIZE_IT Classifier Training")
    print("=" * 60)
    
    # Load data
    print("\n[1/4] Loading training data...")
    texts, labels = load_training_data()
    print(f"  Found {len(texts)} labeled examples")
    
    # Train query classifier
    print("\n[2/4] Training query type classifier...")
    query_classifier = train_query_classifier(texts, labels)
    
    # Build style embeddings
    print("\n[3/4] Building style/framework index...")
    style_index = build_style_embeddings()
    print(f"  Indexed {len(style_index['entries'])} explicit captures")
    
    # Save
    if not args.eval_only:
        print("\n[4/4] Saving models...")
        save_models(query_classifier, style_index, args.output)
    
    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)
    
    # Demo
    print("\nQuick demo - classify some queries:")
    demo_queries = [
        "Wake up, Shepherd",
        "Research distributed LLM",
        "Configure ProtonDrive",
        "Good morning"
    ]
    for query in demo_queries:
        pred = query_classifier.predict([query])[0]
        print(f"  '{query[:40]}...' → {pred}")


if __name__ == "__main__":
    main()
