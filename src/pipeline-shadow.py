#!/usr/bin/env python3
"""
SHADOW PIPELINE — Tier 1: Complete Processing Orchestrator
Part of LOCALIZE_IT: Personal AI Sovereignty

Processes Pi session JSONL files through the complete pipeline:
1. Load raw sessions from ~/.pi/agent/sessions/
2. Filter to target date (default: yesterday)
3. Extract patterns
4. Analyze style
5. Build knowledge graph
6. Generate training corpus
7. Output synthesis report

Usage:
    python3 pipeline-shadow.py --date 2026-06-11
    python3 pipeline-shadow.py --yesterday
    python3 pipeline-shadow.py --all-time
"""

import json
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
SESSIONS_DIR = Path.home() / ".pi" / "agent" / "sessions" / "--home-kinch--"
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = DATA_DIR / "shadow"
LOGS_DIR = PROJECT_DIR / "logs"


def ensure_dirs():
    """Ensure all required directories exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "patterns").mkdir(exist_ok=True)
    (OUTPUT_DIR / "style").mkdir(exist_ok=True)
    (OUTPUT_DIR / "knowledge").mkdir(exist_ok=True)
    (DATA_DIR / "training").mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


def find_sessions_for_date(target_date):
    """Find session files that contain the target date."""
    if not SESSIONS_DIR.exists():
        print(f"ERROR: Sessions directory not found: {SESSIONS_DIR}")
        return []
    
    sessions = []
    for session_file in SESSIONS_DIR.glob("*.jsonl"):
        # Check if file timestamp or content contains target date
        try:
            with open(session_file, 'r') as f:
                content = f.read()
                if target_date in content:
                    sessions.append(session_file)
        except Exception as e:
            print(f"Warning: Could not read {session_file}: {e}")
    
    return sessions


def count_messages_in_sessions(session_files):
    """Count total messages in session files."""
    total = 0
    for sf in session_files:
        try:
            with open(sf, 'r') as f:
                total += sum(1 for line in f if line.strip())
        except Exception:
            pass
    return total


def run_distill_step(name, script, input_dir, output_file):
    """Run a distillation script and return success status."""
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")
    
    cmd = [
        sys.executable,
        str(script),
        "--input", str(input_dir),
        "--output", str(output_file)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            print(f"ERROR: {name} failed")
            if result.stderr:
                print(result.stderr)
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: {name} timed out")
        return False
    except Exception as e:
        print(f"ERROR: {name} exception: {e}")
        return False


def build_training_corpus(patterns_file, style_file, knowledge_file, output_file):
    """Combine all analyses into training corpus format."""
    
    corpus = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "tiers": ["shadow"]
        },
        "system_prompt_additions": [],
        "examples": []
    }
    
    # Load style analysis
    try:
        with open(style_file, 'r') as f:
            style = json.load(f)
        
        style_summary = style.get("summary", "")
        corpus["system_prompt_additions"].append({
            "type": "style_profile",
            "content": style_summary
        })
        
        # Add style preferences
        prefs = []
        if style.get("code_preference", {}).get("preference") == "code-first":
            prefs.append("Provide code examples before explanations")
        if style.get("verbosity", {}).get("level") == "concise":
            prefs.append("Be concise and direct")
        elif style.get("verbosity", {}).get("level") == "verbose":
            prefs.append("Provide detailed explanations")
        if style.get("structure", {}).get("preference") in ["highly_structured", "structured"]:
            prefs.append("Use lists, tables, and clear structure")
        if style.get("directness", {}).get("style") in ["command_direct", "directive"]:
            prefs.append("Respond to commands directly without preamble")
        
        if prefs:
            corpus["system_prompt_additions"].append({
                "type": "preferences",
                "content": "\n".join(f"- {p}" for p in prefs)
            })
            
    except Exception as e:
        print(f"Warning: Could not load style file: {e}")
    
    # Load patterns
    try:
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        
        # Add common query patterns
        if patterns.get("patterns", {}).get("query_patterns"):
            qp = patterns["patterns"]["query_patterns"]
            for pattern_type, items in qp.items():
                if items and len(items) > 0:
                    corpus["system_prompt_additions"].append({
                        "type": f"pattern_{pattern_type}",
                        "content": f"User frequently asks for {pattern_type.replace('_', ' ')}"
                    })
    except Exception as e:
        print(f"Warning: Could not load patterns file: {e}")
    
    # Load knowledge
    try:
        with open(knowledge_file, 'r') as f:
            knowledge = json.load(f)
        
        # Add familiar topics
        familiar = knowledge.get("expertise", {}).get("familiar", [])
        if familiar:
            corpus["system_prompt_additions"].append({
                "type": "familiar_topics",
                "content": f"User is familiar with: {', '.join(familiar[:10])}"
            })
        
        # Add knowledge gaps as learning opportunities
        gaps = knowledge.get("knowledge_gaps", [])
        if gaps:
            gap_text = "User is actively learning:\n" + "\n".join(
                f"- {g['topic']} (asked {g['times_asked']} times)" 
                for g in gaps[:5]
            )
            corpus["system_prompt_additions"].append({
                "type": "knowledge_gaps",
                "content": gap_text
            })
    except Exception as e:
        print(f"Warning: Could not load knowledge file: {e}")
    
    # Write corpus
    with open(output_file, 'w') as f:
        json.dump(corpus, f, indent=2)
    
    return corpus


def generate_report(date_str, patterns_file, style_file, knowledge_file, corpus_file, message_count):
    """Generate human-readable synthesis report."""
    
    report_file = LOGS_DIR / f"shadow-synthesis-{date_str}.md"
    
    lines = [
        f"# Shadow Synthesis Report",
        f"## Date: {date_str}",
        f"## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        f"### Session Statistics",
        f"- Messages processed: {message_count}",
        "",
        "### Files Generated",
        f"- Patterns: `{patterns_file}`",
        f"- Style Analysis: `{style_file}`",
        f"- Knowledge Graph: `{knowledge_file}`",
        f"- Training Corpus: `{corpus_file}`",
        ""
    ]
    
    # Add style summary
    try:
        with open(style_file, 'r') as f:
            style = json.load(f)
        lines.append("### Style Profile")
        lines.append("```")
        lines.append(style.get("summary", "No style data"))
        lines.append("```")
        lines.append("")
    except:
        lines.append("*Style analysis unavailable*")
        lines.append("")
    
    # Add top patterns
    try:
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        
        lines.append("### Behavioral Patterns")
        insights = patterns.get("insights", {})
        lines.append(f"- Primary interaction mode: {insights.get('primary_mode', 'unknown')}")
        lines.append(f"- Correction rate: {insights.get('correction_rate', 0):.1f}%")
        lines.append(f"- Tool diversity: {insights.get('tool_diversity', 0)} tools")
        lines.append("")
    except:
        lines.append("*Pattern analysis unavailable*")
        lines.append("")
    
    # Add knowledge summary
    try:
        with open(knowledge_file, 'r') as f:
            knowledge = json.load(f)
        
        lines.append("### Knowledge Profile")
        diversity = knowledge.get("diversity", {})
        lines.append(f"- Focus type: {diversity.get('focus', 'unknown')}")
        lines.append(f"- Total topics: {diversity.get('total_topics', 0)}")
        lines.append(f"- Top topics: {', '.join(diversity.get('top_topics', [])[:5])}")
        lines.append("")
    except:
        lines.append("*Knowledge graph unavailable*")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "### Next Steps",
        "1. Review training corpus: " + str(corpus_file),
        "2. Run LoRA training when corpus reaches sufficient size",
        "3. Review synthesis reports weekly for trends",
        "",
        f"*Next shadow run: tomorrow*",
    ])
    
    with open(report_file, 'w') as f:
        f.write('\n'.join(lines))
    
    return report_file


def main():
    parser = argparse.ArgumentParser(
        description="LOCALIZE_IT Shadow Pipeline — Process Pi sessions into training data"
    )
    parser.add_argument(
        "--date",
        help="Process sessions for specific date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--yesterday",
        action="store_true",
        help="Process yesterday's sessions (default)"
    )
    parser.add_argument(
        "--all-time",
        action="store_true",
        help="Process all available session data"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip corpus generation (faster for testing)"
    )
    
    args = parser.parse_args()
    
    # Determine target date
    if args.all_time:
        target_date = "all"
        date_str = datetime.now().strftime("%Y-%m-%d")
        print(f"Processing ALL available session data...")
    elif args.date:
        target_date = args.date
        date_str = target_date
        print(f"Processing sessions for {target_date}...")
    else:
        # Default to yesterday
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
        date_str = target_date
        print(f"Processing yesterday's sessions ({target_date})...")
    
    # Ensure directories exist
    ensure_dirs()
    
    # Find sessions
    if args.all_time:
        session_input = SESSIONS_DIR
        print(f"Sessions directory: {session_input}")
    else:
        session_input = SESSIONS_DIR
        print(f"Looking for sessions containing: {target_date}")
    
    if not session_input.exists():
        print(f"ERROR: Session directory not found: {session_input}")
        sys.exit(1)
    
    # Count messages
    all_sessions = list(session_input.glob("*.jsonl"))
    message_count = count_messages_in_sessions(all_sessions)
    print(f"Found {len(all_sessions)} session files with ~{message_count} messages")
    
    if message_count == 0:
        print("WARNING: No messages found. Check session directory.")
        sys.exit(0)
    
    # Define output files
    patterns_file = OUTPUT_DIR / "patterns" / f"{date_str}.json"
    style_file = OUTPUT_DIR / "style" / f"{date_str}.json"
    knowledge_file = OUTPUT_DIR / "knowledge" / f"{date_str}.json"
    corpus_file = DATA_DIR / "training" / f"corpus-{date_str}.json"
    
    # Run pipeline steps
    success = True
    
    # Step 1: Extract patterns
    if not run_distill_step(
        "Pattern Extraction",
        PROJECT_DIR / "src" / "distill" / "extract-patterns.py",
        session_input,
        patterns_file
    ):
        success = False
    
    # Step 2: Analyze style
    if not run_distill_step(
        "Style Analysis",
        PROJECT_DIR / "src" / "distill" / "analyze-style.py",
        session_input,
        style_file
    ):
        success = False
    
    # Step 3: Build knowledge graph
    if not run_distill_step(
        "Knowledge Graph",
        PROJECT_DIR / "src" / "distill" / "build-knowledge.py",
        session_input,
        knowledge_file
    ):
        success = False
    
    # Step 4: Build training corpus
    if not args.quick and success:
        print(f"\n{'='*60}")
        print("STEP: Building Training Corpus")
        print(f"{'='*60}")
        
        try:
            corpus = build_training_corpus(
                patterns_file, style_file, knowledge_file, corpus_file
            )
            print(f"✓ Training corpus: {corpus_file}")
            print(f"  - System prompt additions: {len(corpus['system_prompt_additions'])}")
        except Exception as e:
            print(f"WARNING: Corpus generation failed: {e}")
    
    # Generate report
    print(f"\n{'='*60}")
    print("STEP: Generating Synthesis Report")
    print(f"{'='*60}")
    
    report_file = generate_report(
        date_str,
        patterns_file,
        style_file,
        knowledge_file,
        corpus_file if not args.quick else "N/A",
        message_count
    )
    print(f"✓ Report: {report_file}")
    
    # Final summary
    print(f"\n{'='*60}")
    print("SHADOW PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"\nDate processed: {date_str}")
    print(f"Messages analyzed: {message_count}")
    print(f"\nOutputs:")
    print(f"  Patterns:     {patterns_file}")
    print(f"  Style:        {style_file}")
    print(f"  Knowledge:    {knowledge_file}")
    if not args.quick:
        print(f"  Corpus:       {corpus_file}")
    print(f"  Report:       {report_file}")
    print(f"\nStatus: {'✓ SUCCESS' if success else '⚠ PARTIAL'}")


if __name__ == "__main__":
    main()
