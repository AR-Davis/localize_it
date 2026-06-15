#!/usr/bin/env python3
"""
BUILD-EXPLICIT-CORPUS — Combine all explicit captures into training corpus
Part of LOCALIZE_IT: Personal AI Sovereignty

Aggregates styles, frameworks, contexts, voices from Tier 3 into corpus.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
EXPLICIT_DIR = PROJECT_DIR / "data" / "explicit"
OUTPUT_DIR = PROJECT_DIR / "data" / "training"


def load_jsonl(filepath: Path) -> list:
    """Load all entries from a JSONL file."""
    entries = []
    if not filepath.exists():
        return entries
    
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def build_style_additions(styles: list) -> list:
    """Convert style captures to system prompt additions."""
    additions = []
    
    for style in styles:
        # Skip entries without required fields
        if 'name' not in style:
            print(f"  ⚠️ Skipping style without 'name' field: {style.get('raw_input', 'unknown')[:50]}...")
            continue
        
        description = style.get('description', style.get('raw_input', 'No description'))
        
        content = f"""Working Style: {style['name']}
{description}"""
        
        examples = style.get('examples', [])
        if examples:
            content += f"\n\nExamples:\n" + "\n".join(f"- {ex}" for ex in examples[:3])
        
        additions.append({
            "type": "style_profile",
            "name": style['name'],
            "content": content,
            "captured_at": style.get('timestamp') or style.get('captured_at')
        })
    
    return additions


def build_framework_additions(frameworks: list) -> list:
    """Convert framework captures to system prompt additions."""
    additions = []
    
    for fw in frameworks:
        # Skip entries without required fields
        if 'name' not in fw:
            print(f"  ⚠️ Skipping framework without 'name' field: {fw.get('raw_input', 'unknown')[:50]}...")
            continue
        
        description = fw.get('description', fw.get('raw_input', 'No description'))
        steps = fw.get('steps', [])
        triggers = fw.get('triggers', [])
        
        content = f"""Framework: {fw['name']}
{description}

"""
        if steps:
            content += "Steps:\n"
            for i, step in enumerate(steps, 1):
                content += f"{i}. {step}\n"
        
        if triggers:
            content += f"\nUse when: {', '.join(triggers)}"
        
        additions.append({
            "type": "decision_framework",
            "name": fw['name'],
            "content": content,
            "captured_at": fw.get('timestamp') or fw.get('captured_at')
        })
    
    return additions


def build_context_additions(contexts: list) -> list:
    """Convert context captures to system prompt additions."""
    additions = []
    
    for ctx in contexts:
        # Skip entries without required fields
        if 'project' not in ctx:
            print(f"  ⚠️ Skipping context without 'project' field: {ctx.get('raw_input', 'unknown')[:50]}...")
            continue
        
        project = ctx['project']
        stack = ctx.get('stack', 'Not specified')
        
        content = f"""Project Context: {project}
Stack: {stack}"""
        
        patterns = ctx.get('patterns', [])
        if patterns:
            content += f"\nPatterns: {', '.join(patterns)}"
        
        conventions = ctx.get('conventions', [])
        if conventions:
            content += f"\nConventions: {', '.join(conventions)}"
        
        additions.append({
            "type": "project_context",
            "name": project,
            "content": content,
            "captured_at": ctx.get('timestamp') or ctx.get('captured_at')
        })
    
    return additions


def build_voice_additions(voices: list) -> list:
    """Convert voice captures to system prompt additions."""
    additions = []
    
    for voice in voices:
        # Skip entries without required fields
        if 'name' not in voice:
            print(f"  ⚠️ Skipping voice without 'name' field: {voice.get('raw_input', 'unknown')[:50]}...")
            continue
        
        traits = voice.get('traits', [])
        markers = voice.get('markers', [])
        examples = voice.get('examples', [])
        
        content = f"""Voice/Persona: {voice['name']}"""
        
        if traits:
            content += f"\nTraits: {', '.join(traits)}"
        
        if markers:
            content += f"\nMarkers: {', '.join(markers)}"
        
        if examples:
            content += f"\n\nExample phrases:\n" + "\n".join(f"- {ex}" for ex in examples[:3])
        
        additions.append({
            "type": "voice_profile",
            "name": voice['name'],
            "content": content,
            "captured_at": voice.get('timestamp') or voice.get('captured_at')
        })
    
    return additions


def load_all_explicit() -> dict:
    """Load all explicit captures."""
    data = {
        "styles": [],
        "frameworks": [],
        "contexts": [],
        "voices": []
    }
    
    # Load styles
    styles_file = EXPLICIT_DIR / "styles" / "styles.jsonl"
    if styles_file.exists():
        data["styles"] = load_jsonl(styles_file)
    
    # Load frameworks
    frameworks_file = EXPLICIT_DIR / "frameworks" / "frameworks.jsonl"
    if frameworks_file.exists():
        data["frameworks"] = load_jsonl(frameworks_file)
    
    # Load contexts
    contexts_file = EXPLICIT_DIR / "contexts" / "contexts.jsonl"
    if contexts_file.exists():
        data["contexts"] = load_jsonl(contexts_file)
    
    # Load voices
    voices_file = EXPLICIT_DIR / "voices" / "voices.jsonl"
    if voices_file.exists():
        data["voices"] = load_jsonl(voices_file)
    
    return data


def build_corpus(data: dict) -> dict:
    """Build unified training corpus from all explicit captures."""
    
    corpus = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "tiers": ["explicit"],
            "sources": {
                "styles": len(data["styles"]),
                "frameworks": len(data["frameworks"]),
                "contexts": len(data["contexts"]),
                "voices": len(data["voices"])
            }
        },
        "system_prompt_additions": []
    }
    
    # Add all captures
    corpus["system_prompt_additions"].extend(build_style_additions(data["styles"]))
    corpus["system_prompt_additions"].extend(build_framework_additions(data["frameworks"]))
    corpus["system_prompt_additions"].extend(build_context_additions(data["contexts"]))
    corpus["system_prompt_additions"].extend(build_voice_additions(data["voices"]))
    
    return corpus


def main():
    parser = argparse.ArgumentParser(
        description="Build training corpus from explicit captures"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUT_DIR / "corpus-explicit.json"),
        help="Output corpus file"
    )
    parser.add_argument(
        "--merge-shadow",
        action="store_true",
        help="Merge with existing shadow corpus"
    )
    
    args = parser.parse_args()
    
    print("Loading explicit captures...")
    data = load_all_explicit()
    
    total = sum(len(v) for v in data.values())
    print(f"Found {total} explicit captures:")
    print(f"  Styles: {len(data['styles'])}")
    print(f"  Frameworks: {len(data['frameworks'])}")
    print(f"  Contexts: {len(data['contexts'])}")
    print(f"  Voices: {len(data['voices'])}")
    
    print("\nBuilding corpus...")
    corpus = build_corpus(data)
    
    # Merge with shadow if requested
    if args.merge_shadow:
        shadow_corpus_file = OUTPUT_DIR / "corpus-*.json"
        import glob
        shadow_files = glob.glob(str(shadow_corpus_file))
        
        if shadow_files:
            # Get most recent
            most_recent = max(shadow_files, key=lambda x: Path(x).stat().st_mtime)
            print(f"Merging with: {most_recent}")
            
            with open(most_recent, 'r') as f:
                shadow = json.load(f)
            
            corpus["system_prompt_additions"].extend(
                shadow.get("system_prompt_additions", [])
            )
            corpus["metadata"]["tiers"].append("shadow")
            corpus["metadata"]["merged_from"] = most_recent
    
    # Save corpus
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(corpus, f, indent=2)
    
    print(f"\n✓ Corpus saved: {output_path}")
    print(f"  System prompt additions: {len(corpus['system_prompt_additions'])}")
    print(f"  Tiers: {', '.join(corpus['metadata']['tiers'])}")
    
    # Generate summary report
    summary_file = output_path.with_suffix('.md')
    with open(summary_file, 'w') as f:
        f.write(f"""# Explicit Corpus Report
Generated: {corpus['metadata']['generated_at']}

## Sources
""")
        for source, count in corpus['metadata']['sources'].items():
            f.write(f"- {source}: {count}\n")
        
        f.write(f"""
## System Prompt Additions ({len(corpus['system_prompt_additions'])})

""")
        for addition in corpus['system_prompt_additions']:
            f.write(f"### {addition['type']}: {addition.get('name', 'unnamed')}\n\n")
            f.write(f"{addition['content']}\n\n---\n\n")
    
    print(f"  Summary: {summary_file}")


if __name__ == "__main__":
    main()
