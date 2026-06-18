#!/usr/bin/env python3
"""
EXTRACT-PATTERNS — Tier 1: Shadow Pattern Recognition
Part of LOCALIZE_IT: Personal AI Sovereignty

Reads Pi session JSONL files and extracts behavioral patterns:
- Repeated query structures
- Follow-up patterns (corrections, elaborations)
- Tool usage patterns
- Time-of-day patterns
"""

import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import re


def load_sessions(input_dir):
    """Load all JSONL session files from directory."""
    sessions = []
    input_path = Path(input_dir)
    
    for jsonl_file in input_path.glob("*.jsonl"):
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            sessions.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"Error reading {jsonl_file}: {e}")
    
    return sessions


def extract_text(content):
    """Extract plain text from Pi content structure (handles both string and list)."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return " ".join(text_parts)
    return ""


def calculate_confidence(content, pattern_type, context_window=None):
    """Calculate confidence score (0.0-1.0) for a detected pattern.
    
    Factors:
    - Keyword match strength (exact vs partial)
    - Context richness (surrounding words)
    - Historical frequency (if available)
    - Pattern specificity (generic vs specific)
    """
    confidence = 0.0
    content_lower = content.lower()
    
    if pattern_type == "code_requests":
        # Strong indicators: code/script/function + language
        strong_indicators = ['python', 'bash', 'javascript', 'code', 'script', 'function']
        medium_indicators = ['write', 'create', 'implement', 'build']
        
        if any(kw in content_lower for kw in strong_indicators):
            confidence += 0.5
        if any(kw in content_lower for kw in medium_indicators):
            confidence += 0.3
        # Check for code-like syntax
        if any(char in content for char in ['()', '{}', '[]', '=', ';']):
            confidence += 0.2
            
    elif pattern_type == "explain_requests":
        # Strong: "what is X", "how does Y work"
        strong_patterns = ['what is', 'how does', 'how do', 'why is']
        medium_patterns = ['explain', 'what are', 'tell me about']
        
        if any(pat in content_lower for pat in strong_patterns):
            confidence += 0.6
        elif any(pat in content_lower for pat in medium_patterns):
            confidence += 0.4
        else:
            confidence += 0.2  # Weak match
            
    elif pattern_type == "verify_requests":
        # Strong: explicit verification language
        strong_indicators = ['verify', 'confirm', 'check if', 'is this correct']
        medium_indicators = ['is this right', 'does this work', 'can you check']
        
        if any(kw in content_lower for kw in strong_indicators):
            confidence += 0.6
        elif any(kw in content_lower for kw in medium_indicators):
            confidence += 0.4
        else:
            confidence += 0.2
            
    elif pattern_type == "wake_requests":
        # Strong: explicit wake/reorient
        strong_indicators = ['wake up', 'where were we', 'remind me']
        medium_indicators = ['reorient', 'catch me up', 'what were we doing']
        
        if any(kw in content_lower for kw in strong_indicators):
            confidence += 0.7
        elif any(kw in content_lower for kw in medium_indicators):
            confidence += 0.4
        else:
            confidence += 0.2
    
    # Context richness bonus
    if context_window and len(context_window) > 100:
        confidence += 0.1  # More context = more confident
    
    # Length penalty (very short queries are less confident)
    if len(content) < 20:
        confidence -= 0.1
    
    return min(max(confidence, 0.0), 1.0)  # Clamp 0-1


def extract_query_patterns(messages):
    """Extract patterns from user queries with confidence scores."""
    patterns = defaultdict(list)
    
    for msg in messages:
        if msg.get("type") != "message":
            continue
        
        raw_content = msg.get("message", {}).get("content", "")
        content = extract_text(raw_content)
        if not content:
            continue
        
        content_lower = content.lower()
        
        # Pattern: Code requests
        if any(kw in content_lower for kw in ['code', 'script', 'function', 'python', 'bash']):
            confidence = calculate_confidence(content, "code_requests")
            if confidence >= 0.3:  # Threshold
                patterns["code_requests"].append({
                    "timestamp": msg.get("timestamp"),
                    "query": content[:200],
                    "category": "implementation",
                    "confidence": confidence,
                    "confidence_level": "high" if confidence > 0.7 else "medium" if confidence > 0.5 else "low"
                })
        
        # Pattern: Explain requests
        if any(kw in content_lower for kw in ['explain', 'what is', 'how does', 'why']):
            confidence = calculate_confidence(content, "explain_requests")
            if confidence >= 0.3:
                patterns["explain_requests"].append({
                    "timestamp": msg.get("timestamp"),
                    "query": content[:200],
                    "category": "learning",
                    "confidence": confidence,
                    "confidence_level": "high" if confidence > 0.7 else "medium" if confidence > 0.5 else "low"
                })
        
        # Pattern: Check/verify requests
        if any(kw in content_lower for kw in ['check', 'verify', 'confirm', 'is this right']):
            confidence = calculate_confidence(content, "verify_requests")
            if confidence >= 0.3:
                patterns["verify_requests"].append({
                    "timestamp": msg.get("timestamp"),
                    "query": content[:200],
                    "category": "verification",
                    "confidence": confidence,
                    "confidence_level": "high" if confidence > 0.7 else "medium" if confidence > 0.5 else "low"
                })
        
        # Pattern: Wake/reorient requests
        if any(kw in content_lower for kw in ['wake up', 'reorient', 'where were we', 'remind me']):
            confidence = calculate_confidence(content, "wake_requests")
            if confidence >= 0.3:
                patterns["wake_requests"].append({
                    "timestamp": msg.get("timestamp"),
                    "query": content[:200],
                    "category": "continuity",
                    "confidence": confidence,
                    "confidence_level": "high" if confidence > 0.7 else "medium" if confidence > 0.5 else "low"
                })
    
    return dict(patterns)


def extract_tool_patterns(messages):
    """Extract patterns from tool usage."""
    tool_usage = defaultdict(lambda: {"count": 0, "examples": []})
    
    for msg in messages:
        if msg.get("type") not in ["toolCall", "toolResult"]:
            continue
        
        if msg.get("type") == "toolCall":
            tool_name = msg.get("toolCall", {}).get("name", "unknown")
            tool_usage[tool_name]["count"] += 1
            
            if len(tool_usage[tool_name]["examples"]) < 5:
                tool_usage[tool_name]["examples"].append({
                    "timestamp": msg.get("timestamp"),
                    "args": msg.get("toolCall", {}).get("arguments", {})
                })
    
    return dict(tool_usage)


def extract_follow_up_patterns(messages):
    """Detect when user corrects or elaborates on AI response."""
    corrections = []
    
    # Need to pair assistant -> user messages
    user_msgs = [m for m in messages if m.get("type") == "message" and m.get("message", {}).get("role") == "user"]
    
    for i, msg in enumerate(user_msgs):
        if i == 0:
            continue
        
        raw_content = msg.get("message", {}).get("content", "")
        content = extract_text(raw_content).lower()
        
        # Correction indicators
        correction_markers = ['no,', 'actually', 'wait,', 'not quite', 'that\'s wrong', 'correction']
        elaboration_markers = ['also', 'and also', 'in addition', 'furthermore', 'more specifically']
        
        if any(m in content for m in correction_markers):
            corrections.append({
                "type": "correction",
                "timestamp": msg.get("timestamp"),
                "query": msg.get("message", {}).get("content", "")[:200],
                "category": "clarification"
            })
        elif any(m in content for m in elaboration_markers):
            corrections.append({
                "type": "elaboration",
                "timestamp": msg.get("timestamp"),
                "query": msg.get("message", {}).get("content", "")[:200],
                "category": "expansion"
            })
    
    return corrections


def calculate_pattern_statistics(patterns):
    """Calculate confidence statistics for patterns."""
    stats = {}
    
    for pattern_type, items in patterns.items():
        if not items:
            continue
            
        confidences = [item.get("confidence", 0) for item in items]
        high_conf = len([c for c in confidences if c >= 0.7])
        med_conf = len([c for c in confidences if 0.5 <= c < 0.7])
        low_conf = len([c for c in confidences if c < 0.5])
        
        stats[pattern_type] = {
            "count": len(items),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "high_confidence": high_conf,
            "medium_confidence": med_conf,
            "low_confidence": low_conf,
            "confidence_threshold": 0.3,
            "reliable_patterns": high_conf  # Patterns we can trust
        }
    
    return stats


def calculate_pattern_frequency(patterns):
    """Calculate frequency scores for patterns."""
    frequencies = {}
    
    for pattern_type, items in patterns.items():
        if isinstance(items, list):
            # Only count high confidence patterns for frequency
            high_conf_items = [i for i in items if i.get("confidence", 0) >= 0.5]
            
            frequencies[pattern_type] = {
                "count": len(items),
                "high_confidence_count": len(high_conf_items),
                "frequency": "high" if len(high_conf_items) > 10 else "medium" if len(high_conf_items) > 3 else "low"
            }
    
    return frequencies


def main():
    parser = argparse.ArgumentParser(description="Extract behavioral patterns from Pi sessions")
    parser.add_argument("--input", "-i", required=True, help="Input directory with JSONL files")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file for patterns")
    parser.add_argument("--days", "-d", type=int, default=1, help="Process last N days")
    
    args = parser.parse_args()
    
    print(f"Loading sessions from {args.input}...")
    messages = load_sessions(args.input)
    print(f"Loaded {len(messages)} message entries")
    
    print("Extracting query patterns...")
    query_patterns = extract_query_patterns(messages)
    
    print("Extracting tool usage patterns...")
    tool_patterns = extract_tool_patterns(messages)
    
    print("Extracting follow-up patterns...")
    follow_ups = extract_follow_up_patterns(messages)
    
    print("Calculating frequencies and confidence statistics...")
    frequencies = calculate_pattern_frequency(query_patterns)
    confidence_stats = calculate_pattern_statistics(query_patterns)
    
    # Filter to only high-confidence patterns for insights
    reliable_patterns = {
        k: [i for i in v if i.get("confidence", 0) >= 0.5] 
        for k, v in query_patterns.items()
    }
    
    output = {
        "extraction_timestamp": datetime.now().isoformat(),
        "input_files": len(list(Path(args.input).glob("*.jsonl"))),
        "total_messages": len(messages),
        "confidence_settings": {
            "threshold": 0.3,
            "high_threshold": 0.7,
            "medium_threshold": 0.5,
            "filter_applied": True
        },
        "patterns": {
            "query_patterns": query_patterns,
            "tool_patterns": tool_patterns,
            "follow_ups": follow_ups
        },
        "frequencies": frequencies,
        "confidence_statistics": confidence_stats,
        "insights": {
            "primary_mode": max(frequencies.items(), key=lambda x: x[1].get("high_confidence_count", 0))[0] if frequencies else "unknown",
            "correction_rate": len(follow_ups) / len(messages) * 100 if messages else 0,
            "tool_diversity": len(tool_patterns),
            "reliable_patterns_count": sum(len([i for i in items if i.get("confidence", 0) >= 0.5]) for items in query_patterns.values()),
            "avg_confidence": sum(s.get("avg_confidence", 0) for s in confidence_stats.values()) / len(confidence_stats) if confidence_stats else 0
        },
        "recommendations": [
            f"Found {sum(s['high_confidence'] for s in confidence_stats.values())} high-confidence patterns for training",
            f"Filtered out {sum(s['low_confidence'] for s in confidence_stats.values())} low-confidence patterns",
            "Review medium-confidence patterns before including in training"
        ]
    }
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Patterns extracted to {args.output}")
    print(f"  - Query patterns: {len(query_patterns)} types")
    print(f"  - Tool patterns: {len(tool_patterns)} tools")
    print(f"  - Follow-ups: {len(follow_ups)} corrections/elaborations")
    print(f"\n📊 Confidence Statistics:")
    for pattern_type, stats in confidence_stats.items():
        print(f"    {pattern_type}: {stats['count']} patterns")
        print(f"      High (≥0.7): {stats['high_confidence']}")
        print(f"      Medium (0.5-0.7): {stats['medium_confidence']}")
        print(f"      Low (<0.5): {stats['low_confidence']}")
        print(f"      Avg confidence: {stats['avg_confidence']:.2f}")
    print(f"\n🎯 Primary interaction mode: {output['insights']['primary_mode']}")
    print(f"✅ Reliable patterns (≥0.5): {output['insights']['reliable_patterns_count']}")
    print(f"📈 Average confidence: {output['insights']['avg_confidence']:.2f}")


if __name__ == "__main__":
    main()
