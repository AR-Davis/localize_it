#!/usr/bin/env python3
"""
CAPTURE-CONTEXT — Tier 3: Project Context Capture
Part of LOCALIZE_IT: Personal AI Sovereignty

Captures project-specific context, stack, and preferences.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / "Projects" / "localize_it" / "data" / "explicit" / "contexts"


def ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def capture_context(project: str, stack: str, patterns: list = None, conventions: list = None) -> dict:
    """Capture project-specific context."""
    
    entry = {
        "type": "context_capture",
        "project": project,
        "stack": stack,
        "patterns": patterns or [],
        "conventions": conventions or [],
        "captured_at": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    return entry


def save_context(entry: dict):
    ensure_dir()
    
    contexts_file = DATA_DIR / "contexts.jsonl"
    with open(contexts_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    safe_name = entry["project"].replace(' ', '_').replace('/', '_')
    context_file = DATA_DIR / f"{safe_name}.json"
    with open(context_file, 'w') as f:
        json.dump(entry, f, indent=2)
    
    return contexts_file, context_file


def list_contexts():
    ensure_dir()
    contexts = []
    contexts_file = DATA_DIR / "contexts.jsonl"
    
    if not contexts_file.exists():
        return contexts
    
    with open(contexts_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    contexts.append({
                        "project": entry.get("project"),
                        "stack": entry.get("stack", "")[:40],
                        "captured_at": entry.get("captured_at", "")[:10]
                    })
                except json.JSONDecodeError:
                    continue
    
    return contexts


def main():
    parser = argparse.ArgumentParser(
        description="Capture project-specific context for LOCALIZE_IT"
    )
    parser.add_argument("--project", "-p", required=True,
                       help="Project name (e.g., 'DOMM', 'BlueskyBots')")
    parser.add_argument("--stack", "-s", required=True,
                       help="Tech stack (e.g., 'Rust, TUI, Offline-first')")
    parser.add_argument("--patterns", nargs='*',
                       help="Code patterns used (e.g., 'modular', 'event-driven')")
    parser.add_argument("--conventions", nargs='*',
                       help="Project conventions (e.g., 'snake_case', 'no unwrap')")
    parser.add_argument("--list", action="store_true",
                       help="List all captured contexts")
    
    args = parser.parse_args()
    
    if args.list:
        contexts = list_contexts()
        if not contexts:
            print("No contexts captured yet.")
            return
        
        print("\nCaptured Contexts:")
        print("=" * 60)
        for c in contexts:
            print(f"\n{c['project']}")
            print(f"  Stack: {c['stack']}...")
            print(f"  Captured: {c['captured_at']}")
        return
    
    entry = capture_context(
        project=args.project,
        stack=args.stack,
        patterns=args.patterns,
        conventions=args.conventions
    )
    
    contexts_file, context_file = save_context(entry)
    
    print(f"✓ Context captured: {args.project}")
    print(f"  Database: {contexts_file}")
    print(f"  Individual: {context_file}")
    
    print(f"\nProject: {entry['project']}")
    print(f"Stack: {entry['stack']}")
    if entry['patterns']:
        print(f"Patterns: {', '.join(entry['patterns'])}")
    if entry['conventions']:
        print(f"Conventions: {', '.join(entry['conventions'])}")


if __name__ == "__main__":
    main()
