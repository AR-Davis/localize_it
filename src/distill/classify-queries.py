#!/usr/bin/env python3
"""
CLASSIFY-QUERIES — Distinguish learning vs meta vs social patterns
Part of LOCALIZE_IT: Personal AI Sovereignty

Categorizes user queries into:
- LEARNING: Information seeking (what, how, why)
- META: Checking AI state (still here, you with me)
- SOCIAL: Greetings, sign-offs, pleasantries
- DIRECTIVE: Commands (create, fix, show)
- VERIFICATION: Confirmations (is this right, check this)
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict


def extract_text(content):
    """Extract plain text from Pi content structure."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return " ".join(text_parts)
    return ""


def classify_query(text):
    """Classify a query into categories."""
    text_lower = text.lower().strip()
    
    # META patterns - checking AI state/connection
    meta_patterns = [
        r'^still\s', r'^still\?', r'^still here', r'^still with me',
        r'^you there', r'^you here', r'^you with me',
        r'^lookin\b', r'^looking\b', r'^how.*lookin',
        r'^we good', r'^all good', r'^there\?', r'^here\?',
        r'^you ok', r'^you good', r'^status\?'
    ]
    
    # SOCIAL patterns - greetings, sign-offs
    social_patterns = [
        r'^good morning', r'^morning', r'^hey.*shepherd', r'^hi.*shepherd',
        r'^good night', r'^night.*shepherd', r'^sign.*off',
        r'^logging.*out', r'^going.*bed', r'^back.*later',
        r'^hello\b', r'^hi\b', r'^hey\b'
    ]
    
    # DIRECTIVE patterns - commands
    directive_patterns = [
        r'^(create|build|write|fix|make|show|give|tell|run|check|verify)\b',
        r'^let\s+us', r'^lets', r'^help\s+me'
    ]
    
    # LEARNING patterns - information seeking
    learning_patterns = [
        r'^(what|how|why|when|where|who|which)\s',
        r'^(explain|describe|clarify|tell\s+me\s+about)',
        r'^(is|are|does|do|can|could|would|will)\s',
        r'\?$'  # Ends with question mark (catch-all)
    ]
    
    # VERIFICATION patterns - checking correctness
    verify_patterns = [
        r'(right\?|correct\?|is that right)',
        r'(does that make sense|am i understanding)',
        r'(confirm|verify|check|validate)'
    ]
    
    import re
    
    # Check each category (in order of specificity)
    for pattern in meta_patterns:
        if re.search(pattern, text_lower):
            return "META", "connection_check", 0.9
    
    for pattern in social_patterns:
        if re.search(pattern, text_lower):
            return "SOCIAL", "greeting_or_signoff", 0.85
    
    for pattern in directive_patterns:
        if re.search(pattern, text_lower):
            return "DIRECTIVE", "command", 0.9
    
    for pattern in verify_patterns:
        if re.search(pattern, text_lower):
            return "VERIFICATION", "correctness_check", 0.8
    
    for pattern in learning_patterns:
        if re.search(pattern, text_lower):
            return "LEARNING", "information_seeking", 0.75
    
    return "OTHER", "unclassified", 0.5


def load_and_classify(input_dir):
    """Load sessions and classify all user queries."""
    classifications = defaultdict(list)
    stats = defaultdict(int)
    
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
                            text = extract_text(raw_content)
                            
                            if not text or len(text) < 3:
                                continue
                            
                            category, subtype, confidence = classify_query(text)
                            
                            classifications[category].append({
                                "text": text[:150],
                                "timestamp": entry.get("timestamp"),
                                "subtype": subtype,
                                "confidence": confidence
                            })
                            stats[category] += 1
                            
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {jsonl_file}: {e}")
    
    return classifications, stats


def analyze_meta_patterns(meta_queries):
    """Analyze meta/connection check patterns."""
    patterns = defaultdict(int)
    
    for q in meta_queries:
        text = q["text"].lower()
        if "still" in text:
            patterns["still_check"] += 1
        elif "lookin" in text or "looking" in text:
            patterns["status_check"] += 1
        elif "there" in text or "here" in text:
            patterns["presence_check"] += 1
        elif "good" in text:
            patterns["wellness_check"] += 1
        else:
            patterns["other_meta"] += 1
    
    return dict(patterns)


def analyze_social_patterns(social_queries):
    """Analyze greeting/sign-off patterns."""
    patterns = defaultdict(int)
    
    for q in social_queries:
        text = q["text"].lower()
        if "morning" in text:
            patterns["morning_greeting"] += 1
        elif "night" in text or "goodnight" in text:
            patterns["night_signoff"] += 1
        elif any(x in text for x in ["hey", "hi", "hello"]):
            patterns["casual_greeting"] += 1
        elif "back" in text or "later" in text:
            patterns["temporary_departure"] += 1
        else:
            patterns["other_social"] += 1
    
    return dict(patterns)


def analyze_structure_depth(queries):
    """Analyze how structured vs freeform the queries are."""
    structured_markers = 0
    freeform_markers = 0
    
    for q in queries:
        text = q["text"] if isinstance(q, dict) else q
        
        # Structured indicators
        if any(text.startswith(m) for m in ['1.', '2.', '3.', '- ', '* ', '##']):
            structured_markers += 2
        elif 'table' in text.lower() or 'list' in text.lower():
            structured_markers += 1
        
        # Freeform indicators  
        if len(text.split('.')) == 1 and len(text.split('?')) == 1:
            freeform_markers += 1
    
    total = len(queries) if queries else 1
    structure_ratio = structured_markers / total
    
    if structure_ratio > 0.5:
        return "highly_structured", structure_ratio
    elif structure_ratio > 0.2:
        return "moderately_structured", structure_ratio
    else:
        return "freeform", structure_ratio


def main():
    parser = argparse.ArgumentParser(
        description="Classify user queries into learning/meta/social/directive categories"
    )
    parser.add_argument("--input", "-i", required=True, help="Input directory with JSONL files")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file")
    
    args = parser.parse_args()
    
    print(f"Loading and classifying queries from {args.input}...")
    classifications, stats = load_and_classify(args.input)
    
    print(f"Classified {sum(stats.values())} queries:")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    # Analyze sub-patterns
    meta_analysis = analyze_meta_patterns(classifications.get("META", []))
    social_analysis = analyze_social_patterns(classifications.get("SOCIAL", []))
    
    # Calculate percentages
    total = sum(stats.values())
    percentages = {cat: round(count/total*100, 1) for cat, count in stats.items()}
    
    # Analyze structure in learning queries specifically
    learning_structure = analyze_structure_depth(classifications.get("LEARNING", []))
    
    output = {
        "total_queries": total,
        "categories": {
            cat: {
                "count": len(items),
                "percentage": percentages.get(cat, 0),
                "examples": items[:5]  # First 5 examples
            }
            for cat, items in classifications.items()
        },
        "analysis": {
            "meta_patterns": meta_analysis,
            "social_patterns": social_analysis,
            "learning_structure": {
                "style": learning_structure[0],
                "ratio": round(learning_structure[1], 2)
            }
        },
        "insights": {
            "primary_mode": max(stats.items(), key=lambda x: x[1])[0] if stats else "unknown",
            "social_ratio": round((stats.get("SOCIAL", 0) + stats.get("META", 0)) / total * 100, 1) if total else 0,
            "learning_depth": "deep" if stats.get("LEARNING", 0) > total * 0.3 else "surface",
            "directive_tendency": "high" if stats.get("DIRECTIVE", 0) > total * 0.3 else "low"
        }
    }
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Classification saved to {args.output}")
    print(f"\nKey Insights:")
    print(f"  - Primary interaction mode: {output['insights']['primary_mode']}")
    print(f"  - Social/meta ratio: {output['insights']['social_ratio']}% (connection + learning)")
    print(f"  - Learning style: {output['insights']['learning_depth']} ({learning_structure[0]})")
    print(f"  - Directive tendency: {output['insights']['directive_tendency']}")


if __name__ == "__main__":
    main()
