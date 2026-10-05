#!/usr/bin/env python3
"""
capture_router.py — LOCALIZE_IT multi-tier capture router.

Receives a capture event, classifies it, scores it, and routes it to:
- fast path (persona_prefix injection)
- slow path (nightly synthesis / LoRA / RAG)
- action items (Corraler/Tracker queue)

This is the learning-layer equivalent of the Mycelium decision_service.
"""

import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone

HOME = Path.home()
LOCALIZE_DIR = HOME / "Projects" / "localize_it"
CORPUS_DIR = LOCALIZE_DIR / "mycelium-library" / "localize-it-corpus"

# Candidate locations for the shared corpus consumed by the gateway.
# Watts' target is ~/Mycelium-Shared/mycelium-library/localize-it-corpus/.
# Until that Syncthing folder exists, fall back to the grove-commons synced copy.
SHARED_CORPUS_CANDIDATES = [
    HOME / "Mycelium-Shared" / "mycelium-library" / "localize-it-corpus",
    HOME / "grove-commons" / "MYCELIUM" / "localize-it-corpus",
]
PRIVATE_CORPUS_DIR = HOME / ".mycelium" / "localize-it-corpus"  # node-local private/sealed captures

# Content patterns that must never be written to shared/readable tiers.
SENSITIVE_KEYWORDS = [
    "job hunt", "job search", "resume", "cover letter", "interview",
    "Maine Monitor", "Civitech", "AFP", "Sunrun", "InDepthNH",
    "aaron.davis", "AR-Davis",
]

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b(?:\d{3}[-.\s]?){2}\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_ADDRESS_RE = re.compile(
    r"\b\d+\s+\w+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Circle|Ct|Court)\b",
    re.IGNORECASE,
)


def _is_personal_source(source: str) -> bool:
    """Return True if the source identifies a human operator."""
    source_lower = source.lower()
    return any(ident in source_lower for ident in ("kinch", "user", "human"))


def _contains_pii(content: str) -> bool:
    """Return True if content appears to contain personally identifying information."""
    if _EMAIL_RE.search(content):
        return True
    if _PHONE_RE.search(content):
        return True
    if _SSN_RE.search(content):
        return True
    if _ADDRESS_RE.search(content):
        return True
    if "kinch" in content.lower():
        return True
    return False


def _contains_sensitive_topic(content: str) -> bool:
    """Return True if content touches job-search or other operator-specific topics."""
    content_lower = content.lower()
    return any(kw.lower() in content_lower for kw in SENSITIVE_KEYWORDS)


def _shared_corpus_dir() -> Path:
    """Return the first existing shared-corpus directory."""
    for candidate in SHARED_CORPUS_CANDIDATES:
        if candidate.exists():
            return candidate
    # Default to the first candidate even if it does not exist yet; caller can decide fallback.
    return SHARED_CORPUS_CANDIDATES[0]


SHARED_CORPUS_DIR = _shared_corpus_dir()

# Confidence thresholds
FAST_INJECTION_THRESHOLD = 0.85
SLOW_SYNTHESIS_THRESHOLD = 0.60
ACTION_ITEM_THRESHOLD = 0.70
HUMAN_REVIEW_THRESHOLD = 0.40

# Keyword triggers that bypass the classifier for action items
ACTION_TRIGGERS = [
    r"\b(todo|to do|action item|task|deadline|due)\b",
    r"\b(shift priorities|change focus|need to start|must do)\b",
    r"\b(follow up|remind me|schedule|book)\b",
    r"\b(apply by|submit before|due date|by \d{4}-\d{2}-\d{2})\b",
]

# Category detection rules (hard-coded, override-able by classifier)
CATEGORY_RULES = {
    "preference": {
        "keywords": ["prefer", "like", "want", "don’t want", "hate", "enjoy", "best"],
        "indicators": ["how i like", "preference"],
    },
    "pattern": {
        "keywords": ["usually", "often", "repeatedly", "habit", "always", "pattern"],
        "indicators": ["something i do", "pattern"],
    },
    "framework": {
        "keywords": ["framework", "approach", "method", "process", "workflow", "steps"],
        "indicators": ["how i approach", "framework"],
    },
    "context": {
        "keywords": ["project", "client", "case", "situation", "for this"],
        "indicators": ["project/situation", "context"],
    },
    "discovery": {
        "keywords": ["realized", "learned", "noticed", "discovered", "insight"],
        "indicators": ["something i just realized", "discovery"],
    },
    "research": {
        "keywords": ["research", "investigation", "source", "document", "dataset"],
        "indicators": ["information i gathered", "research"],
    },
    "feedback": {
        "keywords": ["wrong", "incorrect", "correction", "should have", "helpful", "rating"],
        "indicators": ["correction", "feedback", "rating"],
    },
    "pathway": {
        "keywords": ["threshold", "pathway", "fired", "association", "recurring", "priority shift", "state change"],
        "indicators": ["pathway detected", "threshold confirmed", "emotional-relational"],
    },
}


@dataclass
class CaptureEvent:
    id: str
    source: str
    tier: str = ""  # empty sentinel lets __post_init__ detect unset tiers
    type: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Optional[List[str]] = None
    session_id: Optional[str] = None
    timestamp: Optional[str] = None
    related_thread: Optional[str] = None
    # Legacy fields for backward compatibility
    confidence: float = 0.5
    human_confirmed: bool = False

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.id:
            self.id = f"cap-{uuid.uuid4().hex[:12]}"
        if not self.tier:
            if _is_personal_source(self.source):
                self.tier = "private"
            else:
                self.tier = "household"
        # Normalize confidence and human_confirmed from metadata if present
        self.confidence = float(self.metadata.get("confidence", self.confidence))
        self.human_confirmed = bool(self.metadata.get("human_confirmed", self.human_confirmed))


@dataclass
class RoutingDecision:
    tier: str  # fast | slow | action | review
    category: str
    confidence: float
    destinations: List[str]
    priority: int  # 1 = high, 3 = low
    action_required: bool
    action_text: Optional[str]
    expires_at: Optional[str]
    reasoning: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _score_category(content: str, stated_type: str) -> (str, float, List[str]):
    """Apply hard-coded rules to determine category and confidence."""
    content_lower = content.lower()
    scores = {}
    reasoning = []

    for category, rules in CATEGORY_RULES.items():
        score = 0.0
        for kw in rules["keywords"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", content_lower):
                score += 0.15
        for indicator in rules["indicators"]:
            if indicator in content_lower:
                score += 0.25
        if score > 0:
            scores[category] = min(score, 0.95)

    # Stated type gets a strong boost
    if stated_type in CATEGORY_RULES:
        scores[stated_type] = scores.get(stated_type, 0.0) + 0.80
        reasoning.append(f"stated type '{stated_type}' strongly boosts category")

    if not scores:
        return "note", 0.40, ["no strong category signals; defaulting to note"]

    best = max(scores, key=scores.get)
    return best, min(scores[best], 0.95), reasoning + [f"category signals: {scores}"]


def _needs_action_item(content: str, category: str, confidence: float) -> (bool, Optional[str]):
    """Detect action-item triggers."""
    content_lower = content.lower()
    for trigger in ACTION_TRIGGERS:
        if re.search(trigger, content_lower):
            # Extract a plausible action line
            return True, f"Review for action: {content[:100]}"

    # Priority shifts and discoveries often imply action
    if category in ("discovery",) and confidence >= ACTION_ITEM_THRESHOLD:
        if any(kw in content_lower for kw in ["need to", "should", "must", "prioritize"]):
            return True, f"Discovery implies action: {content[:100]}"

    return False, None


def _choose_destinations(category: str, confidence: float, action_required: bool) -> List[str]:
    """Decide where this capture should land."""
    destinations = []

    if confidence >= FAST_INJECTION_THRESHOLD and category in ("preference", "framework", "pattern", "pathway"):
        destinations.append("persona_prefix")

    if confidence >= SLOW_SYNTHESIS_THRESHOLD:
        destinations.append("librarian_index")
        if category in ("preference", "pattern", "framework", "style", "voice", "pathway"):
            destinations.append("training_corpus")

    if category == "feedback":
        destinations.append("classifier_retrain")
        destinations.append("librarian_index")

    if action_required:
        destinations.append("corraler_queue")

    if not destinations:
        destinations.append("librarian_index")  # default archive

    return list(set(destinations))


def _priority(category: str, action_required: bool) -> int:
    if action_required:
        return 1
    if category in ("feedback", "framework"):
        return 1
    if category in ("preference", "pattern"):
        return 2
    return 3


def route(event: CaptureEvent) -> RoutingDecision:
    """Route a capture event through the multi-tier decision pipeline."""
    reasoning = []

    # Step 1: classify category
    category, cat_confidence, cat_reasoning = _score_category(event.content, event.type)
    reasoning.extend(cat_reasoning)

    # Step 2: overall confidence — event confidence dominates; category detection confirms direction
    category_weight = 0.25
    event_weight = 0.75
    overall_confidence = min((cat_confidence * category_weight) + (event.confidence * event_weight), 0.99)
    reasoning.append(f"overall confidence = weighted(category={cat_confidence:.2f} * {category_weight}, event={event.confidence:.2f} * {event_weight})")

    # Human-confirmed captures get a small confidence floor
    if event.human_confirmed and overall_confidence < 0.85:
        overall_confidence = min(overall_confidence + 0.10, 0.99)
        reasoning.append("human_confirmed: +0.10 confidence floor")

    # Step 3: action item detection
    action_required, action_text = _needs_action_item(event.content, category, overall_confidence)
    if action_required:
        reasoning.append(f"action trigger detected: {action_text}")

    # Step 4: choose tier
    if overall_confidence < HUMAN_REVIEW_THRESHOLD:
        tier = "review"
    elif action_required and overall_confidence >= ACTION_ITEM_THRESHOLD:
        tier = "action"
    elif overall_confidence >= FAST_INJECTION_THRESHOLD:
        tier = "fast"
    else:
        tier = "slow"
    reasoning.append(f"selected tier: {tier}")

    # Step 5: destinations
    destinations = _choose_destinations(category, overall_confidence, action_required)
    reasoning.append(f"destinations: {destinations}")

    # Step 6: expiration (optional)
    expires_at = None
    if "deadline" in event.content.lower() or "due" in event.content.lower():
        # In a full implementation, parse actual dates from content
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    return RoutingDecision(
        tier=tier,
        category=category,
        confidence=overall_confidence,
        destinations=destinations,
        priority=_priority(category, action_required),
        action_required=action_required,
        action_text=action_text,
        expires_at=expires_at,
        reasoning=reasoning,
    )


def _corraler_queue_path() -> Path:
    """Return the Corraler pending queue directory for Tracker tasks."""
    return HOME / ".pi" / "corraler" / "queue" / "tracker" / "pending"


def _capture_base_dir(event: CaptureEvent) -> Path:
    """Return the appropriate corpus directory based on privacy tier."""
    if event.tier in ("private", "sealed"):
        return PRIVATE_CORPUS_DIR
    return CORPUS_DIR


def _write_corraler_task(event: CaptureEvent, decision: RoutingDecision) -> Optional[Path]:
    """If the router decided an action is required, write a Tracker task to Corraler."""
    if not decision.action_required or not decision.action_text:
        return None

    queue_dir = _corraler_queue_path()
    queue_dir.mkdir(parents=True, exist_ok=True)

    safe_ts = event.timestamp.replace(":", "-").replace(".", "-") if event.timestamp else "no-timestamp"
    task_id = f"localize-action-{safe_ts}-{event.source}"
    task = {
        "id": task_id,
        "hound": "tracker",
        "title": decision.action_text[:80],
        "status": "pending",
        "priority": decision.priority,
        "category": "localize_it_action",
        "created": datetime.now(timezone.utc).isoformat(),
        "deadline": decision.expires_at,
        "details": {
            "capture_id": event.id,
            "capture_source": event.source,
            "capture_tier": event.tier,
            "capture_type": event.type,
            "capture_content": event.content,
            "routing_decision": decision.to_dict(),
            "notes_file": str(_capture_base_dir(event) / "contexts")
        },
        "notes": f"Auto-generated from LOCALIZE_IT capture router. Review and convert to concrete action or close."
    }

    path = queue_dir / f"{task_id}.json"
    path.write_text(json.dumps(task, indent=2), encoding="utf-8")
    return path


def persist_capture(event: CaptureEvent, decision: RoutingDecision) -> Path:
    """Write the capture and decision to the localize_it corpus."""
    # Privacy-by-default upgrades before choosing a destination.
    if event.type == "feedback" and (len(event.content) > 500 or '"prompt"' in event.content):
        if event.tier in ("public", "household"):
            event.tier = "private"
    if _contains_pii(event.content) and event.tier in ("public", "household"):
        event.tier = "private"
    if _contains_sensitive_topic(event.content) and event.tier in ("public", "household"):
        event.tier = "private"

    base_dir = _capture_base_dir(event)
    dest_dir = base_dir / ("feedback" if event.type == "feedback" else "contexts")
    dest_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "event": asdict(event),
        "decision": decision.to_dict(),
        "routed_at": datetime.now(timezone.utc).isoformat(),
    }

    safe_ts = event.timestamp.replace(":", "-").replace(".", "-") if event.timestamp else "no-timestamp"
    filename = f"{event.source}-{event.type}-{safe_ts}.json"
    path = dest_dir / filename
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    # Also write to Corraler queue if action required (skip sealed tier)
    if event.tier != "sealed":
        corraler_task = _write_corraler_task(event, decision)
        if corraler_task:
            record["corraler_task"] = str(corraler_task)
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    return path


def apply_fast_injection(persona_prefix_path: Optional[Path] = None) -> str:
    """Return the current persona prefix for prepending to prompts.

    Default path is the first existing shared-corpus directory.
    """
    if persona_prefix_path is None:
        persona_prefix_path = _shared_corpus_dir() / "persona_prefix.md"
    if persona_prefix_path.exists():
        return persona_prefix_path.read_text(encoding="utf-8")
    return ""


def _upgrade_legacy_capture(data: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade a pre-v0.1 capture event to the current schema."""
    if "metadata" not in data or data.get("metadata") is None:
        data["metadata"] = {}
    if "confidence" in data and "confidence" not in data["metadata"]:
        data["metadata"]["confidence"] = data.pop("confidence")
    if "human_confirmed" in data and "human_confirmed" not in data["metadata"]:
        data["metadata"]["human_confirmed"] = data.pop("human_confirmed")
    for key in ("id", "source", "tier", "type", "content"):
        data.setdefault(key, "")
    if not data.get("id"):
        data["id"] = f"cap-{uuid.uuid4().hex[:12]}"
    if not data.get("tier"):
        data["tier"] = "household"
    return data


def main():
    """CLI: read a JSON capture from stdin or a file and print the routing decision."""
    import sys

    if len(sys.argv) > 1:
        raw = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    data = json.loads(raw)
    data = _upgrade_legacy_capture(data)
    event = CaptureEvent(**data)
    decision = route(event)
    path = persist_capture(event, decision)

    output = {
        "event": asdict(event),
        "decision": decision.to_dict(),
        "persisted_to": str(path),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
