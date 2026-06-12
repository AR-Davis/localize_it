#!/usr/bin/env python3
"""
BUILD-KNOWLEDGE — Tier 1: Knowledge Graph Construction
Part of LOCALIZE_IT: Personal AI Sovereignty

Builds a knowledge graph from Pi sessions:
- Topics user asks about frequently
- Concepts that appear in multiple contexts
- Relationships between topics
- Knowledge gaps (repeated questions)
"""

import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
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


def load_sessions(input_dir):
    """Load all session messages."""
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
                        if entry.get("type") == "message":
                            raw_content = entry.get("message", {}).get("content", "")
                            messages.append({
                                "role": entry.get("message", {}).get("role"),
                                "content": extract_text(raw_content),
                                "timestamp": entry.get("timestamp")
                            })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {jsonl_file}: {e}")
    
    return messages


def extract_topics(messages):
    """Extract topics/concepts from messages using simple keyword extraction."""
    
    # Technical topics (based on your work)
    tech_topics = [
        'python', 'javascript', 'bash', 'shell', 'script', 'code',
        'git', 'github', 'repository', 'commit', 'branch',
        'docker', 'container', 'kubernetes', 'k8s',
        'api', 'rest', 'graphql', 'webhook',
        'database', 'sql', 'postgres', 'sqlite',
        'bluesky', 'bot', 'automation', 'cron',
        'localize', 'training', 'model', 'lora', 'llm',
        'pi', 'shepherd', 'kennel', 'budger', 'programmer',
        'case', 'investigation', 'research', 'osint',
        'finance', 'trading', 'stock', 'portfolio',
        'grove', 'rhubarb', 'watts', 'pecan'
    ]
    
    topic_mentions = defaultdict(lambda: {"count": 0, "contexts": [], "first_seen": None, "last_seen": None})
    
    for msg in messages:
        content_lower = msg["content"].lower()
        
        for topic in tech_topics:
            if topic in content_lower:
                topic_mentions[topic]["count"] += 1
                
                if len(topic_mentions[topic]["contexts"]) < 3:
                    # Extract context (surrounding text)
                    idx = content_lower.find(topic)
                    start = max(0, idx - 50)
                    end = min(len(msg["content"]), idx + len(topic) + 50)
                    context = msg["content"][start:end]
                    topic_mentions[topic]["contexts"].append(context)
                
                if not topic_mentions[topic]["first_seen"]:
                    topic_mentions[topic]["first_seen"] = msg.get("timestamp")
                topic_mentions[topic]["last_seen"] = msg.get("timestamp")
    
    return dict(topic_mentions)


def identify_knowledge_gaps(messages):
    """Identify topics asked about multiple times (knowledge gaps)."""
    
    # Look for repeated questions
    question_patterns = []
    
    for msg in messages:
        if msg.get("role") != "user":
            continue
        
        content = msg["content"].lower()
        
        # Extract question topics
        if '?' in content or any(content.startswith(w) for w in ['what', 'how', 'why', 'where', 'when', 'can', 'could']):
            # Extract key nouns (simple approach)
            words = re.findall(r'\b\w+\b', content)
            key_words = [w for w in words if len(w) > 4 and w not in ['about', 'would', 'could', 'should']]
            
            if key_words:
                question_patterns.append({
                    "topic": " ".join(key_words[:3]),
                    "timestamp": msg.get("timestamp"),
                    "full_question": msg["content"][:150]
                })
    
    # Find repeated question topics
    topic_counts = Counter(q["topic"] for q in question_patterns)
    gaps = [
        {
            "topic": topic,
            "times_asked": count,
            "examples": [q["full_question"] for q in question_patterns if q["topic"] == topic][:2]
        }
        for topic, count in topic_counts.items()
        if count > 1
    ]
    
    return sorted(gaps, key=lambda x: x["times_asked"], reverse=True)[:10]


def build_concept_relationships(topics):
    """Build relationships between topics based on co-occurrence."""
    
    # Simple relationship: topics that appear together
    relationships = []
    topic_names = list(topics.keys())
    
    for i, topic1 in enumerate(topic_names):
        for topic2 in topic_names[i+1:]:
            # If both topics have high counts, they might be related
            if topics[topic1]["count"] > 2 and topics[topic2]["count"] > 2:
                relationships.append({
                    "source": topic1,
                    "target": topic2,
                    "strength": "medium"
                })
    
    return relationships


def identify_expertise_areas(topics):
    """Identify areas where user seems to have knowledge vs where they ask for help."""
    
    # High mention count = user works with this
    # Could cross-reference with code vs question patterns
    
    expertise = {
        "familiar": [],  # Mentioned frequently
        "learning": [],   # Asked questions about
        "exploring": []   # Mentioned a few times
    }
    
    for topic, data in topics.items():
        if data["count"] > 10:
            expertise["familiar"].append(topic)
        elif data["count"] > 5:
            expertise["exploring"].append(topic)
        elif data["count"] > 2:
            expertise["learning"].append(topic)
    
    return expertise


def calculate_topic_diversity(topics):
    """Calculate how broad vs focused the knowledge graph is."""
    
    if not topics:
        return {"diversity": 0, "focus": "unknown"}
    
    total_mentions = sum(t["count"] for t in topics.values())
    unique_topics = len(topics)
    
    # Calculate concentration (are mentions spread evenly or concentrated?)
    sorted_topics = sorted(topics.items(), key=lambda x: x[1]["count"], reverse=True)
    top_3_mentions = sum(t[1]["count"] for t in sorted_topics[:3])
    
    concentration = top_3_mentions / total_mentions if total_mentions else 0
    
    if concentration > 0.5:
        focus = "specialized"
    elif concentration > 0.3:
        focus = "focused"
    else:
        focus = "diverse"
    
    return {
        "diversity": round(unique_topics / total_mentions, 3) if total_mentions else 0,
        "focus": focus,
        "concentration": round(concentration, 2),
        "total_topics": unique_topics,
        "total_mentions": total_mentions,
        "top_topics": [t[0] for t in sorted_topics[:5]]
    }


def main():
    parser = argparse.ArgumentParser(description="Build knowledge graph from Pi sessions")
    parser.add_argument("--input", "-i", required=True, help="Input directory with JSONL files")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file")
    
    args = parser.parse_args()
    
    print(f"Loading sessions from {args.input}...")
    messages = load_sessions(args.input)
    print(f"Loaded {len(messages)} messages")
    
    print("Extracting topics...")
    topics = extract_topics(messages)
    print(f"Found {len(topics)} unique topics")
    
    print("Identifying knowledge gaps...")
    gaps = identify_knowledge_gaps(messages)
    
    print("Building relationships...")
    relationships = build_concept_relationships(topics)
    
    print("Analyzing expertise areas...")
    expertise = identify_expertise_areas(topics)
    
    print("Calculating diversity metrics...")
    diversity = calculate_topic_diversity(topics)
    
    output = {
        "nodes": [
            {
                "id": topic,
                "count": data["count"],
                "contexts": data["contexts"],
                "first_seen": data["first_seen"],
                "last_seen": data["last_seen"]
            }
            for topic, data in topics.items()
            if data["count"] >= 2  # Filter rare mentions
        ],
        "edges": relationships,
        "knowledge_gaps": gaps,
        "expertise": expertise,
        "diversity": diversity
    }
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Knowledge graph saved to {args.output}")
    print(f"  - Nodes: {len(output['nodes'])}")
    print(f"  - Edges: {len(output['edges'])}")
    print(f"  - Knowledge gaps identified: {len(output['knowledge_gaps'])}")
    print(f"  - Focus type: {output['diversity']['focus']}")
    print(f"\nTop topics: {', '.join(output['diversity']['top_topics'][:5])}")


if __name__ == "__main__":
    main()
