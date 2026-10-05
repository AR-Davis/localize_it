#!/usr/bin/env python3
"""
localize_router_service.py — HTTP wrapper for LOCALIZE_IT capture router.

Provides:
- POST /capture  → classify and route a capture event
- POST /feedback → alias for /capture with type=feedback
- GET  /health   → service status
- GET  /prefix   → return current persona_prefix.md contents

Runs on port 11439 by default (separate from Mycelium Console on 11436).
Does not touch ports 11434 (Ollama), 11435 (gateway), or 50052 (RPC).
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

# Allow importing capture_router from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from capture_router import (
    CaptureEvent,
    RoutingDecision,
    route,
    persist_capture,
    apply_fast_injection,
    _shared_corpus_dir,
    CORPUS_DIR,
)

HOST = "0.0.0.0"
PORT = 11439


def _json_response(status: int, body: Dict[str, Any]) -> bytes:
    return json.dumps(body, indent=2).encode("utf-8")


def _handle_capture(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route a capture event and return the decision."""
    # Upgrade legacy schema
    if "metadata" not in data or data.get("metadata") is None:
        data["metadata"] = {}
    if "confidence" in data and "confidence" not in data["metadata"]:
        data["metadata"]["confidence"] = data.pop("confidence")
    if "human_confirmed" in data and "human_confirmed" not in data["metadata"]:
        data["metadata"]["human_confirmed"] = data.pop("human_confirmed")
    for key in ("id", "source", "tier", "type", "content"):
        data.setdefault(key, "")
    if not data.get("id"):
        import uuid
        data["id"] = f"cap-{uuid.uuid4().hex[:12]}"
    if not data.get("tier"):
        data["tier"] = "household"

    event = CaptureEvent(**data)
    decision = route(event)
    path = persist_capture(event, decision)

    return {
        "event": {
            "id": event.id,
            "source": event.source,
            "tier": event.tier,
            "type": event.type,
            "content": event.content,
            "metadata": event.metadata,
            "tags": event.tags,
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "related_thread": event.related_thread,
        },
        "decision": decision.to_dict(),
        "persisted_to": str(path),
    }


class RouterHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args):
        # Quieter logging; rely on file captures for audit trail
        pass

    def _send(self, status: int, body: Dict[str, Any]):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(_json_response(status, body))

    def do_GET(self):
        shared_dir = _shared_corpus_dir()
        if self.path == "/health":
            self._send(200, {
                "status": "ok",
                "service": "localize_router_service",
                "port": PORT,
                "shared_corpus_path": str(shared_dir),
                "shared_corpus_exists": shared_dir.exists(),
                "working_corpus_exists": CORPUS_DIR.exists(),
            })
        elif self.path == "/prefix":
            prefix = apply_fast_injection()
            persona_path = shared_dir / "persona_prefix.md"
            self._send(200, {
                "persona_prefix_path": str(persona_path),
                "exists": persona_path.exists(),
                "content": prefix,
            })
        else:
            self._send(404, {"error": "not found", "path": self.path})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send(400, {"error": "empty body"})
            return

        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            self._send(400, {"error": "invalid json", "detail": str(e)})
            return

        if self.path == "/capture":
            result = _handle_capture(data)
            self._send(200, result)
        elif self.path == "/feedback":
            data["type"] = "feedback"
            data.setdefault("source", "console")
            result = _handle_capture(data)
            self._send(200, result)
        else:
            self._send(404, {"error": "not found", "path": self.path})


def main():
    server = HTTPServer((HOST, PORT), RouterHandler)
    print(f"LOCALIZE_IT router service listening on http://{HOST}:{PORT}")
    print(f"Endpoints: GET /health, GET /prefix, POST /capture, POST /feedback")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
