#!/usr/bin/env python3
"""
RETRAIN_KB_CLASSIFIER — Rebuild the Pupper KB classifier from seed examples
plus feedback collected from real usage.

Usage:
    python3 src/train/retrain_kb_classifier.py

Reads:
- src/train/train_kb_classifier.py (seed examples)
- data/explicit/kb_feedback.jsonl

Writes:
- models/kb_classifier.pkl
- models/kb_classifier_metadata.json
"""

import json
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
MODEL_DIR = PROJECT_DIR / "models"
FEEDBACK_FILE = PROJECT_DIR / "data" / "explicit" / "kb_feedback.jsonl"


def load_seed_examples() -> Tuple[List[str], List[str]]:
    """Import labeled examples from the seed trainer module."""
    sys.path.insert(0, str(PROJECT_DIR / "src" / "train"))
    import importlib
    seed = importlib.import_module("train_kb_classifier")
    return seed.load_kb_training_data()


def load_feedback() -> Tuple[List[str], List[str]]:
    texts = []
    labels = []
    if not FEEDBACK_FILE.exists():
        return texts, labels

    with FEEDBACK_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                query = entry.get("query", "").strip()
                if not query:
                    continue
                # Prefer the correct label if the prediction was wrong
                label = entry.get("correct_label") or entry.get("predicted_label")
                if label:
                    texts.append(query)
                    labels.append(label)
            except json.JSONDecodeError:
                continue
    return texts, labels


def train_classifier(texts: List[str], labels: List[str]) -> Pipeline:
    valid = [(t, l) for t, l in zip(texts, labels) if t.strip()]
    texts = [p[0] for p in valid]
    labels = [p[1] for p in valid]

    print(f"Training on {len(texts)} examples...")
    print(f"Labels: {sorted(set(labels))}")

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 2),
            stop_words='english'
        )),
        ('classifier', MultinomialNB(alpha=0.1))
    ])

    pipeline.fit(texts, labels)
    return pipeline


def save_classifier(pipeline: Pipeline):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_DIR / "kb_classifier.pkl", 'wb') as f:
        pickle.dump(pipeline, f)

    metadata = {
        'trained_at': datetime.now().isoformat(),
        'version': '1.0',
        'labels': sorted(pipeline.classes_.tolist()),
        'purpose': 'RAG assistant query-to-source routing',
    }
    with open(MODEL_DIR / "kb_classifier_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Saved KB classifier to {MODEL_DIR / 'kb_classifier.pkl'}")


def main():
    print("=" * 60)
    print("LOCALIZE_IT KB Classifier Retraining")
    print("=" * 60)

    print("\n[1/3] Loading seed examples...")
    seed_texts, seed_labels = load_seed_examples()
    print(f"  {len(seed_texts)} seed examples")

    print("\n[2/3] Loading user feedback...")
    fb_texts, fb_labels = load_feedback()
    print(f"  {len(fb_texts)} feedback examples")

    texts = seed_texts + fb_texts
    labels = seed_labels + fb_labels

    print("\n[3/3] Training classifier...")
    pipeline = train_classifier(texts, labels)
    save_classifier(pipeline)

    print("\nDemo:")
    for q in [
        "what tools do I have",
        "what arguments does mycelium-control take",
        "what is Shepherd",
        "is the Mycelium up",
        "what is the kennel status",
    ]:
        pred = pipeline.predict([q])[0]
        print(f"  '{q}' → {pred}")


if __name__ == "__main__":
    main()
