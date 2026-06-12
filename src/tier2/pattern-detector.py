#!/usr/bin/env python3
"""
PATTERN-DETECTOR — Tier 2: Active Preference Detection
Part of LOCALIZE_IT: Personal AI Sovereignty

Detects patterns during live sessions and triggers preference prompts:
- Similar queries repeated (3+ times)
- Corrections made to AI output
- Selections between options
- Time-of-day patterns
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def load_recent_sessions(session_dir, hours=24):
    """Load sessions from last N hours."""
    messages = []
    cutoff = datetime.now() - timedelta(hours=hours)
    
    for jsonl_file in Path(session_dir).glob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
            if mtime < cutoff:
                continue
                
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "message":
                            content = entry.get("message", {}).get("content", "")
                            if isinstance(content, list):
                                text = " ".join(item.get("text", "") for item in content if item.get("type") == "text")
                            else:
                                text = content
                            
                            messages.append({
                                "role": entry.get("message", {}).get("role"),
                                "content": text,
                                "timestamp": entry.get("timestamp")
                            })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {jsonl_file}: {e}")
    
    return messages


def detect_repeated_queries(messages, threshold=3):
    """Detect similar queries repeated within the session."""
    user_messages = [m for m in messages if m.get("role") == "user"]
    
    # Extract key topics from queries
    query_topics = defaultdict(list)
    
    for msg in user_messages:
        content = msg.get("content", "").lower()
        
        # Simple topic extraction
        keywords = []
        for word in content.split():
            word = word.strip(".,!?;:()[]{}\"")
            if len(word) > 4 and word not in ['about', 'would', 'could', 'should', 'there', 'where', 'think']:
                keywords.append(word)
        
        topic = " ".join(sorted(set(keywords))[:3])
        if topic:
            query_topics[topic].append(msg)
    
    # Find repeated topics
    repeated = []
    for topic, msgs in query_topics.items():
        if len(msgs) >= threshold:
            repeated.append({
                "pattern": topic,
                "count": len(msgs),
                "examples": [m["content"][:100] for m in msgs[:3]],
                "suggestion": f"It looks like you're working with '{topic}'. Should I remember this focus area?"
            })
    
    return sorted(repeated, key=lambda x: -x["count"])[:5]


def detect_corrections(messages):
    """Detect when user corrects AI output."""
    corrections = []
    
    # Look for assistant -> user message pairs where user corrects
    for i in range(len(messages) - 1):
        current = messages[i]
        next_msg = messages[i + 1]
        
        if current.get("role") != "assistant" or next_msg.get("role") != "user":
            continue
        
        user_content = next_msg.get("content", "").lower()
        
        correction_markers = [
            "no,", "actually", "wait,", "not quite", "that's wrong",
            "correction", "should be", "meant to say", "i meant"
        ]
        
        if any(marker in user_content for marker in correction_markers):
            corrections.append({
                "ai_output": current.get("content", "")[:100],
                "user_correction": next_msg.get("content", "")[:150],
                "suggestion": "I notice a correction pattern. Should I remember this preference?"
            })
    
    return corrections[:5]


def detect_selections(messages):
    """Detect when user selects between options."""
    selections = []
    
    selection_markers = [
        "let's go with", "i'll take", "option", "let's do",
        "go with", "choose", "prefer", "rather"
    ]
    
    for msg in messages:
        if msg.get("role") != "user":
            continue
        
        content = msg.get("content", "").lower()
        
        if any(marker in content for marker in selection_markers):
            # Look for what was selected
            selections.append({
                "selection": msg.get("content", "")[:150],
                "suggestion": f"You selected an option. Is this a preference I should remember?"
            })
    
    return selections[:5]


def check_prompt_threshold(detected_patterns, min_confidence=0.7):
    """Determine if we should prompt user based on detected patterns."""
    
    # Score based on pattern strength
    total_score = 0
    reasons = []
    
    # Repeated queries = strong signal
    for pattern in detected_patterns.get("repeated", []):
        if pattern["count"] >= 5:
            total_score += 0.4
            reasons.append(f"Repeated focus on '{pattern['pattern'][:30]}...'")
        elif pattern["count"] >= 3:
            total_score += 0.2
            reasons.append(f"Multiple queries about '{pattern['pattern'][:30]}...'")
    
    # Corrections = strong signal
    corrections = detected_patterns.get("corrections", [])
    if len(corrections) >= 3:
        total_score += 0.3
        reasons.append(f"{len(corrections)} corrections made")
    elif len(corrections) >= 1:
        total_score += 0.15
        reasons.append("Correction detected")
    
    # Selections = medium signal
    selections = detected_patterns.get("selections", [])
    if len(selections) >= 2:
        total_score += 0.2
        reasons.append("Multiple option selections")
    
    should_prompt = total_score >= min_confidence
    
    return {
        "should_prompt": should_prompt,
        "confidence": round(total_score, 2),
        "reasons": reasons,
        "primary_pattern": detected_patterns.get("repeated", [{}])[0].get("pattern", "general") if detected_patterns.get("repeated") else "general"
    }


def generate_prompt(detection_result):
    """Generate a preference prompt based on detected patterns."""
    
    if not detection_result["should_prompt"]:
        return None
    
    reasons = detection_result["reasons"]
    primary = detection_result["primary_pattern"]
    
    prompt_text = f"""🤔 PREFERENCE DETECTED

I've noticed a pattern in our session:
{chr(10).join(f"• {r}" for r in reasons[:3])}

It seems like you might have a preference for how I handle '{primary[:40]}'.

Would you like me to remember this?

[y] Yes, capture this preference
[n] No, ignore this time  
[r] Refine the description
[l] Learn more (show details)
[s] Skip and don't ask again for this session"""
    
    return {
        "type": "preference_prompt",
        "text": prompt_text,
        "confidence": detection_result["confidence"],
        "category": "inferred_from_behavior",
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(
        description="Detect patterns in recent sessions and suggest preference capture"
    )
    parser.add_argument(
        "--sessions",
        default="~/.pi/agent/sessions/--home-kinch--",
        help="Session directory to analyze"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Lookback period in hours"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file for detected patterns"
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Generate and display preference prompt"
    )
    
    args = parser.parse_args()
    
    session_dir = Path(args.sessions).expanduser()
    
    print(f"Loading sessions from last {args.hours} hours...")
    messages = load_recent_sessions(session_dir, args.hours)
    print(f"Loaded {len(messages)} messages")
    
    if len(messages) < 10:
        print("Not enough messages for pattern detection")
        return
    
    print("\nAnalyzing patterns...")
    
    detected = {
        "repeated": detect_repeated_queries(messages),
        "corrections": detect_corrections(messages),
        "selections": detect_selections(messages)
    }
    
    print(f"\nDetected:")
    print(f"  {len(detected['repeated'])} repeated query patterns")
    print(f"  {len(detected['corrections'])} corrections")
    print(f"  {len(detected['selections'])} selections")
    
    # Check if we should prompt
    result = check_prompt_threshold(detected)
    
    print(f"\nPrompt confidence: {result['confidence']}")
    if result['reasons']:
        print(f"Reasons: {', '.join(result['reasons'])}")
    
    # Generate prompt if requested and threshold met
    if args.prompt and result["should_prompt"]:
        prompt = generate_prompt(result)
        print("\n" + "="*60)
        print(prompt["text"])
        print("="*60)
    elif args.prompt:
        print("\nNo prompt generated (confidence below threshold)")
    
    # Save output if requested
    if args.output:
        output = {
            "timestamp": datetime.now().isoformat(),
            "lookback_hours": args.hours,
            "messages_analyzed": len(messages),
            "patterns": detected,
            "prompt_recommendation": result
        }
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Saved to {args.output}")


if __name__ == "__main__":
    main()
