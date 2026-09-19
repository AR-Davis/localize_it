#!/usr/bin/env python3
"""
kb_retriever.py — Simple keyword retriever for Pupper's offline KB.

Loads the JSON index produced by compile_kb.py and returns the most
relevant chunks/snippets for a given query.

Optional: load a LOCALIZE_IT KB classifier to apply source-type boosts
so questions about scripts, tools, hounds, or mesh prioritize the right
chunks.
"""

import json
import pickle
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

PUPPER_DIR = Path(__file__).parent
HOME = Path.home()


def load_index(path: Path = None) -> Dict:
    if path is None:
        path = PUPPER_DIR / "knowledge_base.json"
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base index not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_kb_classifier(path: Path = None) -> Optional[object]:
    """Load the LOCALIZE_IT KB classifier if available."""
    if path is None:
        path = HOME / "Projects" / "localize_it" / "models" / "kb_classifier.pkl"
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def tokenize(text: str, stopwords: set) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower())
            if t not in stopwords and len(t) > 2]


def classify_query(query: str, classifier, prob_threshold: float = 0.15, max_labels: int = 4) -> Tuple[Optional[str], Optional[Dict[str, float]], List[str]]:
    """Return (primary_label, merged_source_boosts, active_labels).

    Uses the top-K classifier predictions above prob_threshold so questions
    that combine intents (e.g. "tools and scripts") can pull from multiple
    source types. Broad capabilities-style questions are explicitly detected
    so they always merge all relevant source types.
    """
    # Broad capabilities openers should always use the umbrella mix.
    capabilities_patterns = re.compile(
        r"\b(what can you do|tell me what you can do|what are your abilities|"
        r"what do you do|show me what you can do|list your abilities|"
        r"give me an overview of your abilities|how can you help me|"
        r"what are you good at|what is your job|what is your purpose|"
        r"who are you|what can you help me with)\b",
        re.IGNORECASE,
    )
    is_capabilities = bool(capabilities_patterns.search(query))

    if classifier is None:
        return None, None, []
    try:
        probabilities = classifier.predict_proba([query])[0]
        classes = classifier.classes_.tolist()
        primary = classifier.predict([query])[0]

        # Sort by probability descending
        ranked = sorted(zip(classes, probabilities), key=lambda x: x[1], reverse=True)
        if is_capabilities:
            active_labels = [label for label, prob in ranked if prob >= prob_threshold][:max_labels]
            # Ensure the umbrella labels are present even if below threshold
            for umbrella in ("TOOL_LOOKUP", "SCRIPT_INFO", "HOUND_INFO", "STATUS_REQUEST"):
                if umbrella not in active_labels:
                    active_labels.append(umbrella)
        else:
            active_labels = [label for label, prob in ranked if prob >= prob_threshold][:max_labels]

        # Per-label source boost map
        boost_map = {
            "TOOL_LOOKUP": {"tinker": 3.0, "skill": 1.5, "script": 1.5, "persona": 1.0},
            "SCRIPT_INFO": {"script": 4.0, "skill": 1.5, "tinker": 1.0},
            "HOUND_INFO": {"persona": 5.0, "skill": 2.0, "wake": 1.5, "kennel": 1.0},
            "MESH_INFO": {"grove": 4.0, "script": 1.5, "skill": 1.0},
            "STATUS_REQUEST": {"kennel": 3.0, "corraler": 3.0, "wake": 2.0, "skill": 1.0},
            "LEARNING": {"skill": 2.5, "persona": 2.0, "grove": 2.0, "kennel": 1.5, "script": 1.0},
            "OTHER": {},
        }

        merged = {}
        for label in active_labels:
            for src, boost in boost_map.get(label, {}).items():
                merged[src] = max(merged.get(src, 1.0), boost)
        return primary, merged if merged else None, active_labels
    except Exception:
        return None, None, []


def score_chunk(query_terms: List[str], chunk: Dict, stopwords: set,
                source_boosts: Optional[Dict[str, float]] = None) -> float:
    """Score a chunk by term overlap, with title and source-type boosts."""
    term_counts = chunk.get("terms", {})
    title_terms = tokenize(chunk.get("title", ""), stopwords)
    score = 0.0
    for term in query_terms:
        count = term_counts.get(term, 0)
        bonus = 3.0 if term in title_terms else 1.0
        score += count * bonus

    # Apply source-type boost if classifier provided one
    if source_boosts:
        chunk_type = chunk.get("type", "")
        boost = source_boosts.get(chunk_type, 1.0)
        score *= boost

    # Strongly boost summary/overview chunks for direct identity questions
    title_lower = chunk.get("title", "").lower()
    if "summary" in title_lower or "overview" in title_lower:
        score *= 2.5

    # Boost chunks whose source name matches query terms
    source = chunk.get("source", "")
    source_name = Path(source).stem.lower().replace("-", " ").replace("_", " ")
    source_tokens = tokenize(source_name, stopwords)
    matched_source_terms = sum(1 for t in query_terms if t in source_tokens)
    if matched_source_terms > 0:
        score *= 1.0 + (matched_source_terms * 1.2)
        # Penalize if query term is only a prefix/suffix of a longer source name word
        # e.g., "shepherd" in "shepherd-work-tracker" is valid, but we prefer exact source
        source_words = source_name.split()
        exact_word_match = any(t == w for t in query_terms for w in source_words)
        if exact_word_match:
            score *= 1.5
        else:
            score *= 0.7

    text_len = len(chunk.get("text", ""))
    if text_len < 80:
        score *= 0.3
    return score


def extract_snippet(text: str, query_terms: List[str], window: int = 280) -> str:
    """Extract a short snippet around the densest query-term region."""
    if not text or not query_terms:
        return text[:window * 2]

    text_lower = text.lower()
    positions = []
    for term in query_terms:
        for m in re.finditer(re.escape(term), text_lower):
            positions.append((m.start(), m.end()))

    if not positions:
        return text[:window * 2]

    # Find the window that contains the most query term hits
    best_start = 0
    best_count = 0
    for start, _ in positions:
        end = start + window * 2
        count = sum(1 for s, e in positions if s >= start and s < end)
        if count > best_count:
            best_count = count
            best_start = start

    snippet_start = max(0, best_start - window)
    snippet_end = min(len(text), best_start + window)
    snippet = text[snippet_start:snippet_end]
    # Add ellipses if truncated
    prefix = "..." if snippet_start > 0 else ""
    suffix = "..." if snippet_end < len(text) else ""
    return prefix + snippet.strip() + suffix


def retrieve(query: str, index: Dict, top_k: int = 5,
             source_boosts: Optional[Dict[str, float]] = None,
             allowed_types: Optional[set] = None) -> List[Dict]:
    """Return top_k chunks ranked by overlap scoring with optional source boosts and type filter."""
    stopwords = set(index.get("stopwords", []))
    query_terms = tokenize(query, stopwords)
    if not query_terms:
        return []

    chunk_map = {c["id"]: c for c in index["chunks"]}
    scored = []
    for chunk in index["chunks"]:
        chunk_type = chunk.get("type", "")
        if allowed_types and chunk_type not in allowed_types:
            continue
        s = score_chunk(query_terms, chunk, stopwords, source_boosts)
        if s > 0:
            scored.append((s, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, chunk in scored[:top_k]:
        snippet = extract_snippet(chunk.get("text", ""), query_terms)
        results.append({
            "id": chunk["id"],
            "title": chunk.get("title", chunk.get("source", "unknown")),
            "source": chunk.get("source", "unknown"),
            "type": chunk.get("type", "unknown"),
            "entity": chunk.get("entity", ""),
            "text": chunk.get("text", ""),
            "snippet": snippet,
        })
    return results


# Known hound/persona names for disambiguation
HOUND_NAMES = {
    "shepherd", "budger", "digger", "tracker", "flanker", "programmer",
    "tinker", "corraler", "pupper", "builder", "newton", "jobhunter"
}


def disambiguate_hound_chunks(query_terms: List[str], results: List[Dict]) -> List[Dict]:
    """For hound identity queries, prefer chunks whose entity is exactly the hound."""
    matched_hounds = [t for t in query_terms if t in HOUND_NAMES]
    if not matched_hounds:
        return results

    primary = matched_hounds[0]
    exact = []
    related = []
    other = []
    for r in results:
        entity = r.get("entity", "").lower()
        entity_words = set(entity.replace("-", " ").replace("_", " ").split())
        source_name = Path(r.get("source", "")).stem.lower().replace("-", " ").replace("_", " ")
        source_words = set(source_name.split())
        if primary == entity or (primary in entity_words and len(entity_words) == 1):
            exact.append(r)
        elif primary in entity_words or primary in source_words:
            related.append(r)
        else:
            other.append(r)
    return exact + related + other


# Map classifier labels to allowed source types for hard filtering.
ALLOWED_TYPES_BY_LABEL = {
    "TOOL_LOOKUP": {"tinker", "skill", "script", "persona", "wake"},
    "SCRIPT_INFO": {"script", "skill"},
    "HOUND_INFO": {"persona", "skill", "wake", "kennel"},
    "MESH_INFO": {"grove", "skill", "script", "kennel"},
    "STATUS_REQUEST": {"kennel", "corraler", "wake", "skill", "persona"},
    "LEARNING": {"skill", "persona", "grove", "kennel", "script"},
}


def retrieve_with_classifier(query: str, index: Dict, classifier,
                             top_k: int = 5) -> Tuple[List[Dict], Optional[str], List[str]]:
    """Convenience wrapper that classifies then retrieves.

    Returns (results, primary_label, active_labels).
    """
    primary_label, source_boosts, active_labels = classify_query(query, classifier)

    allowed_types = set()
    for label in active_labels:
        allowed_types.update(ALLOWED_TYPES_BY_LABEL.get(label, set()))

    results = retrieve(query, index, top_k=top_k * 3, source_boosts=source_boosts,
                       allowed_types=allowed_types if allowed_types else None)
    results = disambiguate_hound_chunks(tokenize(query, set(index.get("stopwords", []))), results)
    results = results[:top_k]
    return results, primary_label, active_labels


def format_context(results: List[Dict], max_chars: int = 2500,
                   use_snippets: bool = True) -> str:
    """Join retrieved results into a single context string."""
    parts = []
    total = 0
    for r in results:
        text = r.get("snippet" if use_snippets else "text", "").strip()
        if not text:
            continue
        part = f"--- {r.get('source', r.get('title', 'unknown'))} ---\n{text}\n"
        if total + len(part) > max_chars:
            break
        parts.append(part)
        total += len(part)
    return "\n".join(parts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: kb_retriever.py <query>")
        sys.exit(1)
    idx = load_index()
    clf = load_kb_classifier()
    query = " ".join(sys.argv[1:])
    results, label, active_labels = retrieve_with_classifier(query, idx, clf, top_k=5)
    if label:
        print(f"[KB classifier: primary={label}, active={', '.join(active_labels)}]")
    for r in results:
        print(f"=== {r.get('source', r['id'])} ===")
        print(r.get("snippet", "")[:600])
        print()
