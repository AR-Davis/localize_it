#!/usr/bin/env python3
"""
TRAIN_KB_CLASSIFIER — Train a query classifier for the RAG assistant.
Part of LOCALIZE_IT: Personal AI Sovereignty

Maps natural-language system questions to knowledge-base source priorities.

Labels:
- TOOL_LOOKUP    : questions about tools, access lines, inventory
- SCRIPT_INFO    : questions about specific scripts/commands/arguments
- HOUND_INFO     : questions about personas/hounds and their roles
- MESH_INFO      : questions about Mycelium, Grove, Tailscale, nodes
- STATUS_REQUEST : questions about current status/overview
- LEARNING       : general "how does X work" questions
- OTHER          : everything else

Usage:
    python3 src/train/train_kb_classifier.py
"""

import json
import pickle
import re
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
MODEL_DIR = PROJECT_DIR / "models"


def load_kb_training_data() -> Tuple[List[str], List[str]]:
    """Return labeled (query, label) pairs for system-manual retrieval."""

    # Hand-authored examples. Add more as you discover real queries.
    examples = [
        # TOOL_LOOKUP
        ("what tools do I have", "TOOL_LOOKUP"),
        ("what tools are available", "TOOL_LOOKUP"),
        ("what access lines do we have", "TOOL_LOOKUP"),
        ("how do I use tinker-check", "TOOL_LOOKUP"),
        ("what can I do offline", "TOOL_LOOKUP"),
        ("list my tools", "TOOL_LOOKUP"),
        ("what does budger-watch do", "TOOL_LOOKUP"),
        ("how do I run the trading bot", "TOOL_LOOKUP"),
        ("what is khelp", "TOOL_LOOKUP"),
        ("what is sys-doctor", "TOOL_LOOKUP"),
        ("what are your tools and scripts", "TOOL_LOOKUP"),
        ("what tools and scripts do you have", "TOOL_LOOKUP"),
        ("what scripts and tools do you have", "TOOL_LOOKUP"),
        ("list your abilities", "TOOL_LOOKUP"),
        ("what are your tools and scripts", "SCRIPT_INFO"),
        ("what tools and scripts do you have", "SCRIPT_INFO"),
        ("what scripts and tools do you have", "SCRIPT_INFO"),
        ("list your abilities", "SCRIPT_INFO"),

        # SCRIPT_INFO

        # SCRIPT_INFO
        ("what arguments does mycelium-control take", "SCRIPT_INFO"),
        ("how do I use mycelium-control", "SCRIPT_INFO"),
        ("what flags does kennel-status accept", "SCRIPT_INFO"),
        ("what does the kennel script do", "SCRIPT_INFO"),
        ("how do I run kennel-doctor", "SCRIPT_INFO"),
        ("what is the usage of notes-grep", "SCRIPT_INFO"),
        ("what parameters does inference-doctor need", "SCRIPT_INFO"),
        ("how do I start the api gateway", "SCRIPT_INFO"),
        ("what commands does grove-offline have", "SCRIPT_INFO"),
        ("what is the syntax for ai-ask", "SCRIPT_INFO"),
        ("what scripts do you handle", "SCRIPT_INFO"),
        ("list all the scripts you handle", "SCRIPT_INFO"),
        ("what scripts can you run", "SCRIPT_INFO"),

        # HOUND_INFO
        ("what is Shepherd", "HOUND_INFO"),
        ("what does Shepherd do", "HOUND_INFO"),
        ("what is Budger", "HOUND_INFO"),
        ("what is Tracker", "HOUND_INFO"),
        ("which hound handles finance", "HOUND_INFO"),
        ("which hound does case work", "HOUND_INFO"),
        ("what is Pupper", "HOUND_INFO"),
        ("what is Digger", "HOUND_INFO"),
        ("what is Tinker", "HOUND_INFO"),
        ("what is the Kennel", "HOUND_INFO"),
        ("who handles infrastructure", "HOUND_INFO"),
        ("what is your purpose", "HOUND_INFO"),
        ("who are you", "HOUND_INFO"),

        # MESH_INFO
        ("is the Mycelium up", "MESH_INFO"),
        ("is Ember online", "MESH_INFO"),
        ("what is the Mycelium mesh", "MESH_INFO"),
        ("how does the Grove network work", "MESH_INFO"),
        ("is Tailscale connected", "MESH_INFO"),
        ("what nodes are in the mesh", "MESH_INFO"),
        ("is hearth running", "MESH_INFO"),
        ("what is the status of the RPC nodes", "MESH_INFO"),
        ("how do I check the mesh", "MESH_INFO"),
        ("what is prima.cpp", "MESH_INFO"),

        # STATUS_REQUEST
        ("what is the kennel status", "STATUS_REQUEST"),
        ("give me a status report", "STATUS_REQUEST"),
        ("what is wrong", "STATUS_REQUEST"),
        ("how is everything", "STATUS_REQUEST"),
        ("full status", "STATUS_REQUEST"),
        ("pack status", "STATUS_REQUEST"),
        ("what is happening", "STATUS_REQUEST"),
        ("status board", "STATUS_REQUEST"),
        ("corraler digest", "STATUS_REQUEST"),
        ("what are my priorities", "STATUS_REQUEST"),

        # LEARNING
        ("how does the Mycelium work", "LEARNING"),
        ("explain the kennel protocol", "LEARNING"),
        ("how do I set up Tailscale", "LEARNING"),
        ("what is the Coven", "LEARNING"),
        ("how does Corraler schedule jobs", "LEARNING"),
        ("what is the Three Ravens routing", "LEARNING"),
        ("tell me about offline mode", "LEARNING"),
        ("how does inference fallback work", "LEARNING"),

        # OTHER
        ("hello", "OTHER"),
        ("good morning", "OTHER"),
        ("thank you", "OTHER"),
        ("exit", "OTHER"),
        ("what time is it", "OTHER"),
    ]

    texts = [q for q, _ in examples]
    labels = [l for _, l in examples]
    return texts, labels


def train_kb_classifier(texts: List[str], labels: List[str]) -> Pipeline:
    """Train a lightweight query type classifier for KB retrieval."""
    valid = [(t, l) for t, l in zip(texts, labels) if t.strip()]
    texts = [p[0] for p in valid]
    labels = [p[1] for p in valid]

    print(f"Training KB classifier on {len(texts)} examples...")
    print(f"Labels: {sorted(set(labels))}")

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 2),
            stop_words='english'
        )),
        ('classifier', MultinomialNB(alpha=0.1))
    ])

    pipeline.fit(X_train, y_train)
    score = pipeline.score(X_test, y_test)
    print(f"\nAccuracy: {score:.3f}")

    y_pred = pipeline.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    return pipeline


def save_classifier(pipeline: Pipeline, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "kb_classifier.pkl", 'wb') as f:
        pickle.dump(pipeline, f)

    metadata = {
        'trained_at': datetime.now().isoformat(),
        'version': '1.0',
        'labels': sorted(pipeline.classes_.tolist()),
        'purpose': 'RAG assistant query-to-source routing'
    }
    with open(output_dir / "kb_classifier_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Saved KB classifier to {output_dir / 'kb_classifier.pkl'}")


def main():
    print("=" * 60)
    print("LOCALIZE_IT KB Classifier Training")
    print("=" * 60)

    texts, labels = load_kb_training_data()
    pipeline = train_kb_classifier(texts, labels)
    save_classifier(pipeline, MODEL_DIR)

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
