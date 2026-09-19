#!/usr/bin/env python3
"""
compile_kb.py — Build Pupper's offline knowledge base.

Walks the local system docs, scripts, and persona/skill files and compiles
a single markdown file plus a JSON index that Pupper's retriever can use.

Usage:
    python3 compile_kb.py

Outputs:
    ~/.pi/personas/pupper/knowledge_base.md
    ~/.pi/personas/pupper/knowledge_base.json
"""

import json
import re
import subprocess
from pathlib import Path
from typing import List, Dict
from datetime import datetime

PUPPER_DIR = Path(__file__).parent
HOME = Path.home()

KB_PATH = PUPPER_DIR / "knowledge_base.md"
INDEX_PATH = PUPPER_DIR / "knowledge_base.json"

# Directories and file globs to include.
SOURCES = [
    # Scripts in ~/bin (text-ish ones)
    {"dir": HOME / "bin", "glob": "*", "type": "script", "max_lines": 200},
    # Persona WAKE files (session continuity, lower priority for identity questions)
    {"dir": HOME / ".pi" / "personas", "glob": "**/WAKE.md", "type": "wake"},
    # Persona core identity files (high priority for identity questions)
    {"dir": HOME / ".pi" / "personas", "glob": "**/PERSONA.md", "type": "persona"},
    # Skill/persona skill definitions (high priority for capability questions)
    {"dir": HOME / ".pi" / "personas", "glob": "**/SKILL.md", "type": "skill"},
    # Skill docs
    {"dir": HOME / ".pi" / "skills", "glob": "**/SKILL.md", "type": "skill"},
    # Kennel memory / status
    {"dir": HOME / "Projects" / "kennel", "glob": "MEMORY.md", "type": "kennel"},
    {"dir": HOME / "Projects" / "kennel", "glob": "DEPLOYMENT_STATUS.md", "type": "kennel"},
    # Grove commons status
    {"dir": HOME / "grove-commons", "glob": "STATUS/*.md", "type": "grove"},
    {"dir": HOME / "grove-commons", "glob": "MYCELIUM/**/*.md", "type": "grove"},
    # Corraler priorities if present
    {"dir": HOME / ".pi" / "corraler", "glob": "priorities.md", "type": "corraler"},
    # LOCALIZE_IT KB feedback directory
    {"dir": HOME / "Projects" / "localize_it" / "data" / "explicit", "glob": "kb_feedback.jsonl", "type": "corraler"},
]


def looks_like_text(path: Path) -> bool:
    """Heuristic: reject obvious binaries and huge files."""
    try:
        if not path.is_file():
            return False
        if path.is_symlink():
            # Follow symlink only if it points to a small text file
            resolved = path.resolve()
            if not resolved.is_file():
                return False
            path = resolved
        size = path.stat().st_size
        if size == 0 or size > 1_000_000:
            return False
        with path.open("rb") as f:
            sample = f.read(1024)
        if b"\x00" in sample:
            return False
        return True
    except Exception:
        return False


def read_head(path: Path, max_lines: int) -> str:
    """Read up to max_lines, dropping common binary/control noise."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line.rstrip())
        return "\n".join(lines).strip()
    except Exception as e:
        return f"(could not read: {e})"


def resolve_real_path(path: Path) -> Path:
    """Return the file we will actually read."""
    try:
        if path.is_symlink():
            return path.resolve()
    except Exception:
        pass
    return path


def gather_source_docs():
    docs = []
    seen = set()

    for src in SOURCES:
        root = Path(src["dir"])
        glob = src["glob"]
        kind = src["type"]
        max_lines = src.get("max_lines", None)

        if not root.exists():
            continue

        for path in root.rglob(glob) if "**" in glob else root.glob(glob):
            real_path = resolve_real_path(path)
            key = str(real_path)
            if key in seen:
                continue
            seen.add(key)

            if not looks_like_text(real_path):
                continue

            content = read_head(real_path, max_lines or 2000)
            if not content:
                continue

            rel = real_path.relative_to(HOME) if real_path.is_relative_to(HOME) else real_path
            docs.append({
                "source": str(rel),
                "path": str(real_path),
                "type": kind,
                "content": content,
            })

    return docs


def build_markdown(docs):
    lines = [
        "# Pupper Offline Knowledge Base",
        "",
        f"Compiled: {datetime.now().isoformat()}",
        f"Sources: {len(docs)}",
        "",
        "This handbook contains scripts, personas, skills, and system notes.",
        "Pupper answers questions using only the chunks retrieved from this file.",
        "",
    ]

    for doc in docs:
        lines.append(f"## {doc['source']}")
        lines.append(f"**Type:** {doc['type']}  ")
        lines.append(f"**Path:** `{doc['path']}`")
        lines.append("")
        lines.append(doc["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def extract_summary(doc: Dict) -> str:
    """Extract a one-line summary and usage hints for a source document.

    For scripts: use the first comment line that looks like a description,
    and append a compact usage block if a help()/Usage: section is found.
    For markdown docs: use the first H1 or the first non-empty line.
    """
    content = doc["content"]
    kind = doc["type"]
    source = doc["source"]

    # Scripts: look for Description/Summary or first meaningful comment
    if kind == "script":
        lines = content.splitlines()
        desc = None
        usage_lines = []
        in_usage = False
        for i, line in enumerate(lines[:200]):
            stripped = line.strip()
            if stripped.startswith("#") and not stripped.startswith("#!/"):
                candidate = re.sub(r"^#+\s*", "", stripped).strip()
                if candidate and not candidate.lower().startswith(("usage:", "usage ")) and desc is None:
                    desc = candidate
            # Capture Usage: block or show_help echo lines
            low = stripped.lower()
            if "usage:" in low or "show_help" in low or "usage()" in low:
                in_usage = True
            if in_usage:
                # Stop at blank line after usage block, or after reasonable number of lines
                if stripped == "" and len(usage_lines) > 3:
                    break
                usage_lines.append(stripped)
        summary = desc or f"Script: {Path(source).name}"
        if usage_lines:
            usage_text = " ".join(usage_lines)[:300]
            summary += f"\nUsage hints: {usage_text}"
        return summary

    # Markdown: first H1
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    # Fallback: first non-empty line
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]

    return source


def infer_entity(source: str, kind: str) -> str:
    """Infer the entity (script name, persona name, etc.) from source path."""
    p = Path(source)
    if kind in ("persona", "skill", "wake") and len(p.parent.parts) > 0:
        # For ~/.pi/personas/shepherd/SKILL.md entity is "shepherd"
        return p.parent.name.lower()
    if kind == "script":
        return p.stem.lower()
    if kind in ("kennel", "grove", "corraler"):
        return p.stem.lower()
    return p.stem.lower()


def chunk_document(doc: Dict):
    """Split a single source document into chunks by H2 section.

    Preserves the source type (script, persona, skill, kennel, grove, corraler)
    so retrievers can boost by source category. Adds a synthetic summary chunk
    first for reliable identity/role retrieval.
    """
    chunks = []
    content = doc["content"]
    source = doc["source"]
    kind = doc["type"]
    summary = extract_summary(doc)
    entity = infer_entity(source, kind)

    # Synthetic summary chunk — helps answer "what is X?" questions
    chunks.append({
        "id": f"chunk-{len(chunks)}",
        "title": f"{source} — summary",
        "text": f"## {source}\n\nSummary: {summary}\nType: {kind}\nEntity: {entity}",
        "source": source,
        "type": kind,
        "entity": entity,
    })

    # For scripts without H2, the summary is enough
    if kind == "script" and not re.search(r"^##\s+", content, re.MULTILINE):
        return chunks

    pattern = re.compile(r"^##\s+(.*)$", re.MULTILINE)
    parts = pattern.split(content)

    # Preamble before first H2 (skip if we already captured summary)
    if parts[0].strip():
        chunks.append({
            "id": f"chunk-{len(chunks)}",
            "title": f"{source} — overview",
            "text": f"## {source}\n\n{parts[0].strip()}",
            "source": source,
            "type": kind,
            "entity": entity,
        })

    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        chunks.append({
            "id": f"chunk-{len(chunks)}",
            "title": f"{source} — {title}",
            "text": f"## {source}\n### {title}\n\n{text}",
            "source": source,
            "type": kind,
            "entity": entity,
        })

    return chunks


def chunk_all_docs(docs: List[Dict]):
    """Chunk all source documents and preserve their types."""
    chunks = []
    for doc in docs:
        for chunk in chunk_document(doc):
            chunk["id"] = f"chunk-{len(chunks)}"
            chunks.append(chunk)
    return chunks


def build_index(chunks):
    """Build a simple inverted index for fast keyword retrieval."""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "to", "of", "and", "or", "in", "on", "at", "by", "for", "with", "as",
        "this", "that", "these", "those", "it", "its", "from", "up", "down",
        "if", "then", "else", "when", "where", "who", "what", "how", "why",
        "you", "your", "we", "our", "i", "me", "my", "he", "she", "they",
        "them", "his", "her", "their", "do", "does", "did", "can", "could",
        "will", "would", "should", "shall", "may", "might", "must", "have",
        "has", "had", "not", "no", "yes", "so", "but", "yet", "also", "too",
        "very", "just", "now", "here", "there", "all", "any", "some", "many",
        "more", "most", "other", "such", "only", "own", "same", "than", "into",
        "through", "during", "before", "after", "above", "below", "between",
        "about", "out", "off", "over", "under", "again", "further", "once",
    }

    def tokenize(text: str):
        return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in stopwords and len(t) > 2]

    inverted = {}
    for chunk in chunks:
        terms = tokenize(chunk["title"] + " " + chunk["text"])
        term_counts = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        chunk["terms"] = term_counts
        chunk["term_count"] = sum(term_counts.values())
        for term, count in term_counts.items():
            inverted.setdefault(term, []).append({"id": chunk["id"], "count": count})

    return {
        "chunks": chunks,
        "inverted": inverted,
        "stopwords": sorted(stopwords),
        "compiled": datetime.now().isoformat(),
        "version": "1.0",
    }


def main():
    print("Gathering source documents...")
    docs = gather_source_docs()
    print(f"Found {len(docs)} source documents.")

    print("Building knowledge_base.md...")
    md = build_markdown(docs)
    KB_PATH.write_text(md, encoding="utf-8")
    print(f"Wrote {KB_PATH} ({len(md)} chars)")

    print("Chunking and indexing...")
    chunks = chunk_all_docs(docs)
    index = build_index(chunks)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {INDEX_PATH} ({len(index['chunks'])} chunks)")

    # Also copy to pup-wake/offline-ready for minimal-device sync
    offline_ready = HOME / ".pi" / "pup-wake" / "offline-ready"
    offline_ready.mkdir(parents=True, exist_ok=True)
    offline_kb = offline_ready / "knowledge_base.md"
    offline_json = offline_ready / "knowledge_base.json"
    offline_kb.write_text(md, encoding="utf-8")
    offline_json.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Copied offline-ready snapshot to {offline_ready}")


if __name__ == "__main__":
    main()
