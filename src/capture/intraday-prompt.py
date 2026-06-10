#!/usr/bin/env python3
"""
INTRADAY PROMPT — Tier 2: Active preference capture
Part of LOCALIZE_IT: Personal AI Sovereignty

Usage:
    intraday-prompt --detect-preference "user wrote 5 technical docs today"
    intraday-prompt --ask "It looks like you prefer X. Is this true?"
    intraday-prompt --capture "user explicitly stated preference Y"
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
DATA_DIR = PROJECT_DIR / "data" / "intraday"
LOG_FILE = PROJECT_DIR / "logs" / "intraday-capture.log"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().isoformat()
    entry = f"[{timestamp}] {message}"
    print(entry)
    with open(LOG_FILE, 'a') as f:
        f.write(entry + '\n')


def detect_and_prompt(pattern, confidence):
    """
    Detect a potential preference and prompt user for confirmation.
    
    Called when system detects pattern:
    - Similar queries repeated
    - Corrections made to AI output
    - Selections between options
    """
    print(f"\n{'='*60}")
    print("🤔 PREFERENCE DETECTED")
    print(f"{'='*60}")
    print(f"\nPattern: {pattern}")
    print(f"Confidence: {confidence}%")
    print("\nIt looks like you might prefer this approach.")
    print("\nOptions:")
    print("  [y] Yes, remember this")
    print("  [n] No, ignore")
    print("  [r] Refine the description")
    print("  [s] Skip for now")
    
    choice = input("\nSelect: ").strip().lower()
    
    if choice == 'y':
        store_preference(pattern, "detected", confidence)
        print("✓ Preference saved")
        return True
    elif choice == 'r':
        refined = input("Describe your preference: ").strip()
        store_preference(refined, "refined", confidence + 10)
        print("✓ Refined preference saved")
        return True
    else:
        print("Preference not saved")
        return False


def store_preference(preference, source, confidence):
    """Store a confirmed preference"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "preference": preference,
        "source": source,
        "confidence": confidence,
        "category": categorize_preference(preference)
    }
    
    # Append to preferences.jsonl
    pref_file = DATA_DIR / "preferences.jsonl"
    with open(pref_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    log(f"Preference captured: {preference[:50]}...")


def store_pattern(pattern_type, description):
    """Store a detected pattern"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": pattern_type,
        "description": description,
        "frequency": 1  # Increment if exists
    }
    
    pattern_file = DATA_DIR / "patterns.jsonl"
    with open(pattern_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    log(f"Pattern captured: {pattern_type} - {description[:50]}...")


def store_framework(name, description, steps):
    """Store an explicit framework"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "name": name,
        "description": description,
        "steps": steps if isinstance(steps, list) else steps.split(','),
        "uses": 0
    }
    
    framework_file = DATA_DIR / "frameworks.jsonl"
    with open(framework_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    log(f"Framework captured: {name}")


def categorize_preference(preference):
    """Categorize preference by type"""
    pref_lower = preference.lower()
    
    if any(word in pref_lower for word in ['format', 'structure', 'template']):
        return "format"
    elif any(word in pref_lower for word in ['explain', 'detail', 'simple', 'brief']):
        return "explanation"
    elif any(word in pref_lower for word in ['code', 'python', 'bash', 'javascript']):
        return "code"
    elif any(word in pref_lower for word in ['first', 'order', 'sequence']):
        return "ordering"
    else:
        return "general"


def show_stats():
    """Show intraday capture statistics"""
    print(f"\n{'='*60}")
    print("📊 INTRADAY CAPTURE STATS")
    print(f"{'='*60}\n")
    
    # Count preferences
    pref_file = DATA_DIR / "preferences.jsonl"
    if pref_file.exists():
        prefs = [json.loads(line) for line in open(pref_file)]
        print(f"Total preferences: {len(prefs)}")
        
        # By category
        categories = {}
        for p in prefs:
            cat = p.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\nBy category:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")
    else:
        print("No preferences captured yet")
    
    # Count patterns
    pattern_file = DATA_DIR / "patterns.jsonl"
    if pattern_file.exists():
        patterns = [json.loads(line) for line in open(pattern_file)]
        print(f"\nTotal patterns: {len(patterns)}")
    
    # Count frameworks
    framework_file = DATA_DIR / "frameworks.jsonl"
    if framework_file.exists():
        frameworks = [json.loads(line) for line in open(framework_file)]
        print(f"Total frameworks: {len(frameworks)}")
        for fw in frameworks[-5:]:  # Show last 5
            print(f"  - {fw['name']}: {fw['description'][:40]}...")


def main():
    parser = argparse.ArgumentParser(
        description="LOCALIZE_IT Intraday Preference Capture"
    )
    
    parser.add_argument('--detect-preference', type=str,
                       help='Detect and prompt for a preference')
    parser.add_argument('--confidence', type=int, default=70,
                       help='Confidence level (0-100)')
    parser.add_argument('--capture-preference', type=str,
                       help='Directly capture a preference')
    parser.add_argument('--capture-pattern', type=str,
                       help='Capture a pattern')
    parser.add_argument('--pattern-type', type=str, default='behavior',
                       help='Type of pattern')
    parser.add_argument('--capture-framework', type=str,
                       help='Capture a framework')
    parser.add_argument('--framework-desc', type=str,
                       help='Framework description')
    parser.add_argument('--framework-steps', type=str,
                       help='Framework steps (comma-separated)')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.detect_preference:
        detect_and_prompt(args.detect_preference, args.confidence)
    elif args.capture_preference:
        store_preference(args.capture_preference, "explicit", 100)
    elif args.capture_pattern:
        store_pattern(args.pattern_type, args.capture_pattern)
    elif args.capture_framework:
        if not args.framework_steps:
            print("Error: --framework-steps required")
            sys.exit(1)
        store_framework(
            args.capture_framework,
            args.framework_desc or args.capture_framework,
            args.framework_steps
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
