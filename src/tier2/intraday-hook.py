#!/usr/bin/env python3
"""
INTRADAY-HOOK — Tier 2: Pi Session Integration
Part of LOCALIZE_IT: Personal AI Sovereignty

Hooks into Pi sessions to detect patterns in real-time and suggest
preference capture at appropriate moments.

Usage: Called by Pi after each message exchange
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

TIER2_DIR = Path(__file__).parent
DATA_DIR = Path.home() / "Projects" / "localize_it" / "data" / "intraday"
PROMPT_LOG = DATA_DIR / "prompts.jsonl"


def ensure_dirs():
    """Ensure data directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_session_context(session_file: str) -> dict:
    """Load current session context for analysis."""
    context = {
        "message_count": 0,
        "user_messages": [],
        "last_prompt_time": None
    }
    
    session_path = Path(session_file)
    if not session_path.exists():
        return context
    
    try:
        with open(session_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "message":
                        context["message_count"] += 1
                        if entry.get("message", {}).get("role") == "user":
                            content = entry.get("message", {}).get("content", "")
                            if isinstance(content, list):
                                text = " ".join(item.get("text", "") 
                                    for item in content if item.get("type") == "text")
                            else:
                                text = content
                            context["user_messages"].append(text)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error loading session: {e}", file=__import__('sys').stderr)
    
    return context


def check_prompt_cooldown(last_prompt: Optional[str], min_minutes: int = 30) -> bool:
    """Check if enough time has passed since last prompt."""
    if not last_prompt:
        return True
    
    try:
        last_time = datetime.fromisoformat(last_prompt.replace('Z', '+00:00'))
        elapsed = (datetime.now() - last_time.replace(tzinfo=None)).total_seconds() / 60
        return elapsed >= min_minutes
    except:
        return True


def should_suggest_capture(context: dict) -> tuple[bool, str, float]:
    """
    Determine if we should suggest preference capture.
    
    Returns: (should_prompt, reason, confidence)
    """
    messages = context.get("user_messages", [])
    
    if len(messages) < 5:
        return False, "not_enough_messages", 0.0
    
    # Check cooldown
    last_prompt = context.get("last_prompt_time")
    if not check_prompt_cooldown(last_prompt, min_minutes=30):
        return False, "cooldown_active", 0.0
    
    # Pattern 1: Repeated similar questions
    recent = messages[-10:]  # Last 10 messages
    word_sets = [set(m.lower().split()) for m in recent]
    
    overlap_count = 0
    for i, words1 in enumerate(word_sets):
        for words2 in word_sets[i+1:]:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            if overlap > 0.6:  # 60% word overlap
                overlap_count += 1
    
    if overlap_count >= 2:
        return True, "repeated_similar_queries", 0.75
    
    # Pattern 2: Correction language in last message
    last_msg = messages[-1].lower() if messages else ""
    correction_markers = ["no,", "actually", "wait", "that\'s not", "should be"]
    if any(marker in last_msg for marker in correction_markers):
        return True, "likely_correction", 0.70
    
    # Pattern 3: Selection/choice made
    selection_markers = ["let\'s go with", "i\'ll take", "option", "let\'s do"]
    if any(marker in last_msg for marker in selection_markers):
        return True, "selection_made", 0.65
    
    # Pattern 4: Meta questions about preferences
    meta_markers = ["do you remember", "did we", "last time", "usually"]
    if any(marker in last_msg for marker in meta_markers):
        return True, "meta_preference_check", 0.60
    
    return False, "no_pattern_detected", 0.0


def log_prompt_decision(reason: str, confidence: float, triggered: bool):
    """Log prompt decision for analysis."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "confidence": confidence,
        "triggered": triggered
    }
    
    with open(PROMPT_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def suggest_preference_capture(reason: str, confidence: float) -> dict:
    """Generate a suggestion for preference capture."""
    
    suggestions = {
        "repeated_similar_queries": {
            "message": "I notice you've asked about similar topics multiple times. Would you like me to remember your focus area?",
            "category": "topic_focus"
        },
        "likely_correction": {
            "message": "I sense I may not have gotten that quite right. Should I remember how you prefer this explained?",
            "category": "explanation_style"
        },
        "selection_made": {
            "message": "You chose an option. Is this a preference I should remember for next time?",
            "category": "choice_preference"
        },
        "meta_preference_check": {
            "message": "You seem to be checking if I remember something. Should I capture this as a preference?",
            "category": "memory_preference"
        }
    }
    
    suggestion = suggestions.get(reason, {
        "message": "Should I remember this pattern?",
        "category": "general"
    })
    
    return {
        "type": "intraday_suggestion",
        "suggest_capture": True,
        "message": suggestion["message"],
        "category": suggestion["category"],
        "confidence": confidence,
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(
        description="Intraday hook for Pi session integration"
    )
    parser.add_argument(
        "--session-file",
        required=True,
        help="Path to current session JSONL file"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for suggestion (if any)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output if suggestion is triggered"
    )
    
    args = parser.parse_args()
    
    ensure_dirs()
    
    # Load context
    context = load_session_context(args.session_file)
    
    # Check if we should suggest
    should_prompt, reason, confidence = should_suggest_capture(context)
    
    # Log the decision
    log_prompt_decision(reason, confidence, should_prompt)
    
    # Generate output if triggered
    if should_prompt:
        result = suggest_preference_capture(reason, confidence)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        
        if not args.quiet:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))  # Minimal output for piping
    else:
        if not args.quiet:
            print(json.dumps({
                "type": "intraday_suggestion",
                "suggest_capture": False,
                "reason": reason,
                "confidence": confidence
            }, indent=2))


if __name__ == "__main__":
    main()
