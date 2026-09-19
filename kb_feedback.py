#!/usr/bin/env python3
"""
kb_feedback.py — Capture Pupper KB feedback for LOCALIZE_IT training.

Usage:
    python3 kb_feedback.py --query "What does X do?" --label HOUND_INFO --helpful yes
    python3 kb_feedback.py --query "What does X do?" --label HOUND_INFO --helpful no --correct-label SCRIPT_INFO
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

FEEDBACK_FILE = Path.home() / "Projects" / "localize_it" / "data" / "explicit" / "kb_feedback.jsonl"


def log_feedback(query: str, predicted_label: str, helpful: bool, correct_label: str = None):
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)

    correct_labels = None
    if correct_label:
        correct_labels = [l.strip() for l in correct_label.replace(",", " ").split() if l.strip()]
        if not correct_labels:
            correct_labels = None

    entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "predicted_label": predicted_label,
        "helpful": helpful,
        "correct_label": correct_labels,
    }
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Logged feedback to {FEEDBACK_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Log Pupper KB feedback")
    parser.add_argument("--query", required=True, help="The question asked")
    parser.add_argument("--label", required=True, help="Label the classifier predicted")
    parser.add_argument("--helpful", required=True, choices=["yes", "no"], help="Was the routing useful?")
    parser.add_argument("--correct-label", help="What label should it have been?")
    args = parser.parse_args()

    log_feedback(
        query=args.query,
        predicted_label=args.label,
        helpful=args.helpful == "yes",
        correct_label=args.correct_label,
    )


if __name__ == "__main__":
    main()
