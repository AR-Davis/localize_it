#!/usr/bin/env python3
"""
ANALYZE-STYLE — Tier 1: Writing Style Analysis
Part of LOCALIZE_IT: Personal AI Sovereignty

Analyzes user's writing style from Pi sessions:
- Formality level (casual vs formal)
- Code preference (code-first vs explanation-first)
- Verbosity (concise vs detailed)
- Structure preferences (lists, tables, narrative)
"""

import json
import argparse
from pathlib import Path
from collections import Counter
import re


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


def load_user_messages(input_dir):
    """Load only user messages from session files."""
    messages = []
    input_path = Path(input_dir)
    
    for jsonl_file in input_path.glob("*.jsonl"):
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if (entry.get("type") == "message" and 
                            entry.get("message", {}).get("role") == "user"):
                            raw_content = entry.get("message", {}).get("content", "")
                            content = extract_text(raw_content)
                            if content:
                                messages.append({
                                    "content": content,
                                    "timestamp": entry.get("timestamp"),
                                    "session": jsonl_file.name
                                })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {jsonl_file}: {e}")
    
    return messages


def analyze_formality(messages):
    """Analyze formality level of user writing."""
    
    formal_markers = ['would', 'could', 'please', 'thank', 'regards', 'sincerely']
    casual_markers = ['hey', 'hi', 'ok', 'cool', 'yeah', 'nah', 'gonna', 'wanna']
    
    formal_count = 0
    casual_count = 0
    total_words = 0
    
    for msg in messages:
        words = msg["content"].lower().split()
        total_words += len(words)
        
        formal_count += sum(1 for w in words if w in formal_markers)
        casual_count += sum(1 for w in words if w in casual_markers)
    
    if total_words == 0:
        return {"level": "unknown", "score": 0}
    
    formal_rate = formal_count / total_words
    casual_rate = casual_count / total_words
    
    if casual_rate > formal_rate * 2:
        level = "casual"
    elif formal_rate > casual_rate * 2:
        level = "formal"
    else:
        level = "balanced"
    
    return {
        "level": level,
        "formal_rate": round(formal_rate, 4),
        "casual_rate": round(casual_rate, 4),
        "total_words": total_words
    }


def analyze_code_preference(messages):
    """Analyze preference for code vs explanation."""
    
    code_indicators = ['```', 'def ', 'class ', 'import ', 'function', 'script']
    explain_indicators = ['explain', 'what is', 'how does', 'why', 'describe', 'tell me about']
    
    code_count = 0
    explain_count = 0
    
    for msg in messages:
        content_lower = msg["content"].lower()
        
        if any(ind in content_lower for ind in code_indicators):
            code_count += 1
        if any(ind in content_lower for ind in explain_indicators):
            explain_count += 1
    
    total = code_count + explain_count
    if total == 0:
        return {"preference": "balanced", "code_ratio": 0.5}
    
    code_ratio = code_count / total
    
    if code_ratio > 0.6:
        preference = "code-first"
    elif code_ratio < 0.4:
        preference = "explanation-first"
    else:
        preference = "balanced"
    
    return {
        "preference": preference,
        "code_ratio": round(code_ratio, 2),
        "explain_ratio": round(1 - code_ratio, 2),
        "code_requests": code_count,
        "explain_requests": explain_count
    }


def analyze_verbosity(messages):
    """Analyze verbosity level."""
    
    lengths = [len(msg["content"].split()) for msg in messages]
    
    if not lengths:
        return {"level": "unknown", "avg_words": 0}
    
    avg_length = sum(lengths) / len(lengths)
    
    if avg_length < 10:
        level = "very_concise"
    elif avg_length < 25:
        level = "concise"
    elif avg_length < 50:
        level = "moderate"
    else:
        level = "verbose"
    
    return {
        "level": level,
        "avg_words": round(avg_length, 1),
        "min_words": min(lengths) if lengths else 0,
        "max_words": max(lengths) if lengths else 0,
        "median_words": sorted(lengths)[len(lengths)//2] if lengths else 0
    }


def analyze_structure_preference(messages):
    """Analyze preference for structured vs narrative output."""
    
    structure_markers = ['1.', '2.', '3.', '- ', '* ', '##', '###', 'table', 'list']
    narrative_markers = ['paragraph', 'essay', 'story', 'explain in detail', 'write about']
    
    structured_count = 0
    narrative_count = 0
    
    for msg in messages:
        content_lower = msg["content"].lower()
        
        # Check if user provided structured input (suggests they want structured output)
        if any(msg["content"].startswith(m) for m in ['- ', '* ', '1. ', '##']):
            structured_count += 2  # Weight heavier
        elif any(m in content_lower for m in structure_markers):
            structured_count += 1
        
        if any(m in content_lower for m in narrative_markers):
            narrative_count += 1
    
    total = structured_count + narrative_count
    if total == 0:
        return {"preference": "unknown", "structure_score": 0.5}
    
    structure_score = structured_count / total
    
    if structure_score > 0.6:
        preference = "highly_structured"
    elif structure_score > 0.4:
        preference = "structured"
    elif structure_score > 0.2:
        preference = "flexible"
    else:
        preference = "narrative"
    
    return {
        "preference": preference,
        "structure_score": round(structure_score, 2),
        "narrative_score": round(1 - structure_score, 2),
        "structured_requests": structured_count,
        "narrative_requests": narrative_count
    }


def analyze_directness(messages):
    """Analyze how direct/command-style vs conversational the user is."""
    
    command_starters = ['create', 'build', 'write', 'fix', 'make', 'show', 'give', 'tell']
    question_starters = ['what', 'how', 'why', 'when', 'where', 'can you', 'could you']
    
    command_count = 0
    question_count = 0
    
    for msg in messages:
        content_lower = msg["content"].lower().strip()
        first_word = content_lower.split()[0] if content_lower else ""
        
        if first_word in command_starters:
            command_count += 1
        elif any(content_lower.startswith(q) for q in question_starters):
            question_count += 1
    
    total = command_count + question_count
    if total == 0:
        return {"style": "mixed", "directness": 0.5}
    
    directness = command_count / total
    
    if directness > 0.7:
        style = "command_direct"
    elif directness > 0.5:
        style = "directive"
    elif directness > 0.3:
        style = "conversational"
    else:
        style = "question_friendly"
    
    return {
        "style": style,
        "directness": round(directness, 2),
        "command_ratio": round(command_count / len(messages), 2) if messages else 0,
        "question_ratio": round(question_count / len(messages), 2) if messages else 0
    }


def generate_style_summary(analyses):
    """Generate human-readable style summary."""
    
    summary = f"""Style Profile

Formality: {analyses['formality']['level'].replace('_', ' ').title()}
- Formal markers: {analyses['formality']['formal_rate']:.2%}
- Casual markers: {analyses['formality']['casual_rate']:.2%}

Code Preference: {analyses['code_preference']['preference'].replace('-', ' ').title()}
- Code requests: {analyses['code_preference']['code_requests']}
- Explanation requests: {analyses['code_preference']['explain_requests']}

Verbosity: {analyses['verbosity']['level'].replace('_', ' ').title()}
- Average words per message: {analyses['verbosity']['avg_words']}

Structure: {analyses['structure']['preference'].replace('_', ' ').title()}
- Prefers lists/tables: {analyses['structure']['structure_score']:.0%}

Directness: {analyses['directness']['style'].replace('_', ' ').title()}
- Command style: {analyses['directness']['directness']:.0%}
"""
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="Analyze writing style from Pi sessions")
    parser.add_argument("--input", "-i", required=True, help="Input directory with JSONL files")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file")
    
    args = parser.parse_args()
    
    print(f"Loading user messages from {args.input}...")
    messages = load_user_messages(args.input)
    print(f"Found {len(messages)} user messages")
    
    print("Analyzing style...")
    analyses = {
        "formality": analyze_formality(messages),
        "code_preference": analyze_code_preference(messages),
        "verbosity": analyze_verbosity(messages),
        "structure": analyze_structure_preference(messages),
        "directness": analyze_directness(messages)
    }
    
    analyses["summary"] = generate_style_summary(analyses)
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(analyses, f, indent=2)
    
    print(f"\n✓ Style analysis saved to {args.output}")
    print("\n" + analyses["summary"])


if __name__ == "__main__":
    main()
