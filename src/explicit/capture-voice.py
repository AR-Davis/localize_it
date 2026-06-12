#!/usr/bin/env python3
"""
CAPTURE-VOICE — Tier 3: Voice/Persona Capture
Part of LOCALIZE_IT: Personal AI Sovereignty

Captures voice traits, persona characteristics, and communication style.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / "Projects" / "localize_it" / "data" / "explicit" / "voices"


def ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def capture_voice(name: str, traits: list, markers: list = None, examples: list = None, base_model: str = None) -> dict:
    """Capture a voice/persona definition."""
    
    entry = {
        "type": "voice_capture",
        "name": name,
        "traits": traits,
        "markers": markers or [],  # Distinctive markers (e.g., "occasional dog metaphors")
        "examples": examples or [],
        "base_model": base_model or "default",
        "captured_at": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    return entry


def save_voice(entry: dict):
    ensure_dir()
    
    voices_file = DATA_DIR / "voices.jsonl"
    with open(voices_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    safe_name = entry["name"].replace(' ', '_').replace('/', '_')
    voice_file = DATA_DIR / f"{safe_name}.json"
    with open(voice_file, 'w') as f:
        json.dump(entry, f, indent=2)
    
    return voices_file, voice_file


def list_voices():
    ensure_dir()
    voices = []
    voices_file = DATA_DIR / "voices.jsonl"
    
    if not voices_file.exists():
        return voices
    
    with open(voices_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    voices.append({
                        "name": entry.get("name"),
                        "traits": ', '.join(entry.get("traits", [])[:3]),
                        "captured_at": entry.get("captured_at", "")[:10]
                    })
                except json.JSONDecodeError:
                    continue
    
    return voices


def main():
    parser = argparse.ArgumentParser(
        description="Capture a voice/persona for LOCALIZE_IT"
    )
    parser.add_argument("--name", "-n", required=True,
                       help="Voice name (e.g., 'shepherd-refined', 'technical-blogger')")
    parser.add_argument("--traits", "-t", required=True, nargs='+',
                       help="Voice traits (e.g., 'technical', 'enthusiastic', 'brief')")
    parser.add_argument("--markers", "-m", nargs='*',
                       help="Distinctive markers (e.g., 'occasional-dog-metaphors')")
    parser.add_argument("--examples", "-e", nargs='*',
                       help="Example phrases in this voice")
    parser.add_argument("--base-model",
                       help="Base model this voice builds on")
    parser.add_argument("--list", action="store_true",
                       help="List all captured voices")
    
    args = parser.parse_args()
    
    if args.list:
        voices = list_voices()
        if not voices:
            print("No voices captured yet.")
            return
        
        print("\nCaptured Voices:")
        print("=" * 60)
        for v in voices:
            print(f"\n{v['name']}")
            print(f"  Traits: {v['traits']}...")
            print(f"  Captured: {v['captured_at']}")
        return
    
    entry = capture_voice(
        name=args.name,
        traits=args.traits,
        markers=args.markers,
        examples=args.examples,
        base_model=args.base_model
    )
    
    voices_file, voice_file = save_voice(entry)
    
    print(f"✓ Voice captured: {args.name}")
    print(f"  Database: {voices_file}")
    print(f"  Individual: {voice_file}")
    
    print(f"\nTraits: {', '.join(entry['traits'])}")
    if entry['markers']:
        print(f"Markers: {', '.join(entry['markers'])}")


if __name__ == "__main__":
    main()
