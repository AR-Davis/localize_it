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


def extract_query_patterns(messages):
    """Extract patterns from user queries."""
    patterns = defaultdict(list)
    
    for msg in messages:
        if msg.get("type") != "message":
            continue
        
        raw_content = msg.get("message", {}).get("content", "")
        content = extract_text(raw_content)
        if not content:
            continue
        
        # Pattern: Code requests
        if any(kw in content.lower() for kw in ['code', 'script', 'function', 'python', 'bash']):
            patterns["code_requests"].append({
                "timestamp": msg.get("timestamp"),
                "query": content[:200],
                "category": "implementation"
            })
        
        # Pattern: Explain requests
        if any(kw in content.lower() for kw in ['explain', 'what is', 'how does', 'why']):
            patterns["explain_requests"].append({
                "timestamp": msg.get("timestamp"),
                "query": content[:200],
                "category": "learning"
            })
        
        # Pattern: Check/verify requests
        if any(kw in content.lower() for kw in ['check', 'verify', 'confirm', 'is this right']):
            patterns["verify_requests"].append({
                "timestamp": msg.get("timestamp"),
                "query": content[:200],
                "category": "verification"
            })
        
        # Pattern: Wake/reorient requests
        if any(kw in content.lower() for kw in ['wake up', 'reorient', 'where were we', 'remind me']):
            patterns["wake_requests"].append({
                "timestamp": msg.get("timestamp"),
                "query": content[:200],
                "category": "continuity"
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


def calculate_pattern_frequency(patterns):
    """Calculate frequency scores for patterns."""
    frequencies = {}
    
    for pattern_type, items in patterns.items():
        if isinstance(items, list):
            frequencies[pattern_type] = {
                "count": len(items),
                "frequency": "high" if len(items) > 10 else "medium" if len(items) > 3 else "low"
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
    
    print("Calculating frequencies...")
    frequencies = calculate_pattern_frequency(query_patterns)
    
    output = {
        "extraction_timestamp": datetime.now().isoformat(),
        "input_files": len(list(Path(args.input).glob("*.jsonl"))),
        "total_messages": len(messages),
        "patterns": {
            "query_patterns": query_patterns,
            "tool_patterns": tool_patterns,
            "follow_ups": follow_ups
        },
        "frequencies": frequencies,
        "insights": {
            "primary_mode": max(frequencies.items(), key=lambda x: x[1]["count"])[0] if frequencies else "unknown",
            "correction_rate": len(follow_ups) / len(messages) * 100 if messages else 0,
            "tool_diversity": len(tool_patterns)
        }
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
    print(f"  - Primary interaction mode: {output['insights']['primary_mode']}")


if __name__ == "__main__":
    main()
