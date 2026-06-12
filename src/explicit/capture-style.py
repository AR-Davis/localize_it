#!/usr/bin/env python3
"""
CAPTURE-STYLE — Tier 3: Explicit Style Capture
Part of LOCALIZE_IT: Personal AI Sovereignty

Captures complete working styles via explicit command.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / "Projects" / "localize_it" / "data" / "explicit" / "styles"


def ensure_dir():
    """Ensure styles directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def capture_style(name: str, description: str, examples: list = None, tags: list = None) -> dict:
    """Capture a complete working style."""
    
    entry = {
        "type": "style_capture",
        "name": name,
        "description": description,
        "examples": examples or [],
        "tags": tags or [],
        "captured_at": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    return entry


def save_style(entry: dict):
    """Save style to explicit database."""
    ensure_dir()
    
    # Save to JSONL
    styles_file = DATA_DIR / "styles.jsonl"
    with open(styles_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    # Also save as individual file for easy editing
    safe_name = entry["name"].replace(' ', '_').replace('/', '_')
    style_file = DATA_DIR / f"{safe_name}.json"
    with open(style_file, 'w') as f:
        json.dump(entry, f, indent=2)
    
    return styles_file, style_file


def list_styles():
    """List all captured styles."""
    ensure_dir()
    
    styles = []
    styles_file = DATA_DIR / "styles.jsonl"
    
    if not styles_file.exists():
        return styles
    
    with open(styles_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    styles.append({
                        "name": entry.get("name"),
                        "description": entry.get("description", "")[:60],
                        "captured_at": entry.get("captured_at", "")[:10]
                    })
                except json.JSONDecodeError:
                    continue
    
    return styles


def main():
    parser = argparse.ArgumentParser(
        description="Capture a complete working style for LOCALIZE_IT"
    )
    parser.add_argument(
        "--name", "-n",
        required=True,
        help="Style name (e.g., 'technical-writing', 'casual-blogging')"
    )
    parser.add_argument(
        "--description", "-d",
        required=True,
        help="Style description (e.g., 'Concise, code-first, assumes technical reader')"
    )
    parser.add_argument(
        "--examples", "-e",
        nargs='*',
        help="Example phrases in this style"
    )
    parser.add_argument(
        "--tags", "-t",
        nargs='*',
        help="Tags for categorization (e.g., 'professional', 'technical', 'casual')"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all captured styles"
    )
    
    args = parser.parse_args()
    
    if args.list:
        styles = list_styles()
        if not styles:
            print("No styles captured yet.")
            return
        
        print("\nCaptured Styles:")
        print("=" * 60)
        for s in styles:
            print(f"\n{s['name']}")
            print(f"  {s['description']}...")
            print(f"  Captured: {s['captured_at']}")
        return
    
    # Capture new style
    entry = capture_style(
        name=args.name,
        description=args.description,
        examples=args.examples,
        tags=args.tags
    )
    
    styles_file, style_file = save_style(entry)
    
    print(f"✓ Style captured: {args.name}")
    print(f"  Database: {styles_file}")
    print(f"  Individual: {style_file}")
    
    # Show what was captured
    print(f"\nCaptured:")
    print(f"  Name: {entry['name']}")
    print(f"  Description: {entry['description']}")
    if entry['examples']:
        print(f"  Examples: {len(entry['examples'])} provided")
    if entry['tags']:
        print(f"  Tags: {', '.join(entry['tags'])}")


if __name__ == "__main__":
    main()
