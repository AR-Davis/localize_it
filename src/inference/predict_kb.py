#!/usr/bin/env python3
"""
PREDICT_KB — Classify system-manual questions for RAG retrieval.
Part of LOCALIZE_IT: Personal AI Sovereignty

Usage:
    python3 src/inference/predict_kb.py "what tools do I have"
    python3 src/inference/predict_kb.py --interactive
"""

import json
import pickle
import argparse
from pathlib import Path
from typing import Dict, List

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
MODEL_DIR = PROJECT_DIR / "models"

# Map labels to source-type priorities for retrieval boost.
# Higher number = stronger boost.
SOURCE_PRIORITIES = {
    "TOOL_LOOKUP": {
        "tinker": 3.0,
        "skill": 1.5,
        "script": 0.5,
    },
    "SCRIPT_INFO": {
        "script": 4.0,
        "skill": 1.0,
    },
    "HOUND_INFO": {
        "persona": 5.0,
        "skill": 2.0,
        "wake": 0.5,
        "kennel": 0.5,
    },
    "MESH_INFO": {
        "grove": 4.0,
        "script": 1.0,
        "skill": 1.0,
    },
    "STATUS_REQUEST": {
        "kennel": 3.0,
        "corraler": 3.0,
        "wake": 1.5,
        "skill": 0.5,
    },
    "LEARNING": {
        "skill": 2.0,
        "persona": 2.0,
        "grove": 2.0,
        "kennel": 1.5,
    },
    "OTHER": {},
}


def load_kb_classifier(model_dir: Path = MODEL_DIR):
    with open(model_dir / "kb_classifier.pkl", 'rb') as f:
        return pickle.load(f)


def classify_kb(query: str, classifier) -> Dict:
    prediction = classifier.predict([query])[0]
    probabilities = classifier.predict_proba([query])[0]

    top_indices = probabilities.argsort()[-3:][::-1]
    top_labels = [
        {
            'label': classifier.classes_[i],
            'confidence': float(probabilities[i])
        }
        for i in top_indices
    ]

    return {
        'primary': prediction,
        'confidence': float(probabilities[classifier.classes_.tolist().index(prediction)]),
        'top_3': top_labels,
        'source_boosts': SOURCE_PRIORITIES.get(prediction, {}),
    }


def main():
    parser = argparse.ArgumentParser(description="Classify KB queries for source routing")
    parser.add_argument("query", nargs="?", help="Query text to classify")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Interactive mode")
    args = parser.parse_args()

    classifier = load_kb_classifier()

    def process(q: str):
        result = classify_kb(q, classifier)
        print(f"\nQuery: {q}")
        print(f"Primary: {result['primary']} ({result['confidence']:.2f})")
        print("Top 3:")
        for label in result['top_3']:
            print(f"  {label['label']}: {label['confidence']:.2f}")
        if result['source_boosts']:
            print("Source boosts:")
            for source, boost in result['source_boosts'].items():
                print(f"  {source}: {boost}x")

    if args.interactive:
        print("KB Query Classifier (Ctrl+D to exit)")
        while True:
            try:
                q = input("\n> ").strip()
                if q:
                    process(q)
            except (EOFError, KeyboardInterrupt):
                break
    elif args.query:
        process(args.query)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
