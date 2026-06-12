#!/usr/bin/env python3
"""
CAPTURE-FRAMEWORK — Tier 3: Explicit Framework Capture
Part of LOCALIZE_IT: Personal AI Sovereignty

Captures decision frameworks, workflows, and analysis patterns.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / "Projects" / "localize_it" / "data" / "explicit" / "frameworks"


def ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def capture_framework(name: str, description: str, steps: list, triggers: list = None, examples: list = None) -> dict:
    """Capture a decision or analysis framework."""
    
    entry = {
        "type": "framework_capture",
        "name": name,
        "description": description,
        "steps": steps,
        "triggers": triggers or [],  # When to use this framework
        "examples": examples or [],
        "captured_at": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    return entry


def save_framework(entry: dict):
    ensure_dir()
    
    frameworks_file = DATA_DIR / "frameworks.jsonl"
    with open(frameworks_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    safe_name = entry["name"].replace(' ', '_').replace('/', '_')
    framework_file = DATA_DIR / f"{safe_name}.json"
    with open(framework_file, 'w') as f:
        json.dump(entry, f, indent=2)
    
    return frameworks_file, framework_file


def list_frameworks():
    ensure_dir()
    frameworks = []
    frameworks_file = DATA_DIR / "frameworks.jsonl"
    
    if not frameworks_file.exists():
        return frameworks
    
    with open(frameworks_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    frameworks.append({
                        "name": entry.get("name"),
                        "description": entry.get("description", "")[:60],
                        "steps": len(entry.get("steps", [])),
                        "captured_at": entry.get("captured_at", "")[:10]
                    })
                except json.JSONDecodeError:
                    continue
    
    return frameworks


def main():
    parser = argparse.ArgumentParser(
        description="Capture a decision or analysis framework"
    )
    parser.add_argument("--name", "-n", required=True,
                       help="Framework name (e.g., 'architecture-review', 'debug-protocol')")
    parser.add_argument("--description", "-d", required=True,
                       help="What this framework is for")
    parser.add_argument("--steps", "-s", required=True, nargs='+',
                       help="Framework steps (e.g., '1.Constraints 2.Options 3.Decision')")
    parser.add_argument("--triggers", "-t", nargs='*',
                       help="When to use this framework (e.g., 'code review', 'debugging')")
    parser.add_argument("--examples", "-e", nargs='*',
                       help="Example applications of this framework")
    parser.add_argument("--list", action="store_true",
                       help="List all captured frameworks")
    
    args = parser.parse_args()
    
    if args.list:
        frameworks = list_frameworks()
        if not frameworks:
            print("No frameworks captured yet.")
            return
        
        print("\nCaptured Frameworks:")
        print("=" * 60)
        for f in frameworks:
            print(f"\n{f['name']} ({f['steps']} steps)")
            print(f"  {f['description']}...")
            print(f"  Captured: {f['captured_at']}")
        return
    
    entry = capture_framework(
        name=args.name,
        description=args.description,
        steps=args.steps,
        triggers=args.triggers,
        examples=args.examples
    )
    
    frameworks_file, framework_file = save_framework(entry)
    
    print(f"✓ Framework captured: {args.name}")
    print(f"  Database: {frameworks_file}")
    print(f"  Individual: {framework_file}")
    
    print(f"\nSteps:")
    for i, step in enumerate(entry['steps'], 1):
        print(f"  {i}. {step}")


if __name__ == "__main__":
    main()
