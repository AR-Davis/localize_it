#!/usr/bin/env python3
"""
Pupper Terminal — Interactive offline Pupper session.
Pupper is a natural-language troubleshooter for Kinch's systems.
Runs entirely offline via local Ollama or the Mycelium mesh when available.
"""

import os
import sys
import json
import textwrap
import subprocess
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inference import SmartInferenceRouter

PUPPER_DIR = Path(__file__).parent
CORRALER_PUPPER = Path.home() / ".pi" / "corraler" / "pupper"
HOME_BIN = Path.home() / "bin"


def run_cmd(cmd: list[str], timeout: int = 30) -> str:
    """Run a shell command safely and return trimmed output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path.home()),
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"(timed out after {timeout}s)"
    except Exception as e:
        return f"(error: {e})"


def load_digest() -> str:
    path = CORRALER_PUPPER / "digest.md"
    if path.exists():
        return path.read_text()
    return "No digest available."


def load_mycelium_backup() -> str:
    path = CORRALER_PUPPER / "mycelium-backup" / "README.md"
    if path.exists():
        return path.read_text()
    return ""


def classify_intent(query: str) -> str:
    """Classify query intent using simple keyword matching.
    Topic-specific keywords take priority over generic status/check words."""
    q = query.lower()

    # Explicit search intent (prefixes) takes top priority
    if any(x in q for x in ["find my", "search my", "where is my", "where are my", "notes on", "notes about", "grep", "document about", "file with", "file about"]):
        return "search"

    # Full Kennel overview / status board
    if any(x in q for x in ["kennel status", "full status", "status board", "pack status", "all hounds", "overview"]):
        return "overview"

    # Tool inventory / access lines
    if any(x in q for x in ["tools", "access lines", "inventory", "tinker", "what do we have", "available tools"]):
        return "tools"

    # Topic-specific intents before generic status words like "what's wrong"
    if any(x in q for x in ["tailscale", "mycelium", "mesh", "ember", "crow", "wren", "hearth", "ollama", "node"]):
        return "mesh"

    if any(x in q for x in ["trading bot", "continuous trader", "alpaca", "dowdogs", "bot trading", "trade", "trading", "equity", "position"]):
        return "trading"

    if any(x in q for x in ["network", "ping", "ip ", "ssh", "wifi", "internet", "connection", "reach", "online", "offline", "route"]):
        return "network"

    if any(x in q for x in ["disk", "memory", "cpu", "ram", "space", "full", "slow", "system health", "doctor", "diagnostic"]):
        return "system"

    if any(x in q for x in ["kennel", "corraler", "pupper", "shepherd", "hound", "cron", "watchdog", "digest"]):
        return "kennel"

    # Generic status / check intent only if no topic keyword matched
    if any(x in q for x in ["status", "what's wrong", "what is wrong", "how is", "report", "healthy", "check"]):
        return "status"

    # Broader search words (without explicit prefixes)
    if any(x in q for x in ["find", "search", "where is", "notes", "grep", "document", "file"]):
        return "search"

    return "general"


def gather_context(intent: str, query: str) -> str:
    """Run offline diagnostic tools based on intent and return their output."""
    ctx_parts = []

    if intent == "mesh":
        # Put the most actionable checks first so tiny model sees them even if context is truncated
        ctx_parts.append("== Mesh RPC port probes (timeout 2s) ==")
        for host in ["100.90.116.1", "100.97.71.98", "100.83.89.53"]:
            out = run_cmd(["bash", "-c", f"timeout 2 bash -c '</dev/tcp/{host}/50052' && echo open || echo closed"], timeout=5)
            ctx_parts.append(f"{host}:50052 -> {out}")
        ctx_parts.append("\n== Tailscale status (trimmed) ==")
        ts = run_cmd(["tailscale", "status"], timeout=10)
        ctx_parts.append("\n".join(ts.splitlines()[:12]))
        ctx_parts.append("\n== Local mycelium-api (port 11435) ==")
        ctx_parts.append(run_cmd(["bash", "-c", "curl -s --max-time 2 http://localhost:11435/api/status 2>&1 | head -20"], timeout=5))

    elif intent == "kennel":
        ctx_parts.append("== Corraler digest ==")
        ctx_parts.append(load_digest())
        ctx_parts.append("\n== Kennel doctor ==")
        ctx_parts.append(run_cmd([str(HOME_BIN / "kennel-doctor")], timeout=20))
        ctx_parts.append("\n== Key kennel processes ==")
        ctx_parts.append(run_cmd(["bash", "-c", "pgrep -af 'continuous|mycelium|watchdog|ollama' | head -15"], timeout=5))

    elif intent == "overview":
        ctx_parts.append("== Kennel status overview ==")
        ctx_parts.append(run_cmd([str(HOME_BIN / "kennel-status")], timeout=30))

    elif intent == "tools":
        ctx_parts.append("== Tool inventory (Tinker) ==")
        inventory = Path.home() / ".pi" / "personas" / "tinker" / "inventory" / "access-lines.json"
        if inventory.exists():
            data = json.loads(inventory.read_text())
            lines = []
            for a in data.get("access_lines", []):
                lines.append(f"{a['name']}: {a.get('status', 'unknown')}")
            for t in data.get("offline_tools", []):
                lines.append(f"{t['name']}: {t.get('status', 'unknown')} (offline)")
            ctx_parts.append("\n".join(lines))
            reminders = data.get("reminders", [])
            if reminders:
                ctx_parts.append("\n== Attention needed ==")
                for r in reminders:
                    ctx_parts.append(f"• {r['tool']} ({r['priority']}): {r['message']}")
        else:
            ctx_parts.append("(Tinker inventory not found)")

    elif intent == "trading":
        ctx_parts.append("== Bot status script ==")
        ctx_parts.append(run_cmd([str(HOME_BIN / "budger-watch")], timeout=15))
        ctx_parts.append("\n== Recent continuous trader log ==")
        ctx_parts.append(run_cmd(["bash", "-c", "tail -30 /home/kinch/Projects/kennel/logs/continuous_v4.log 2>/dev/null || echo 'no log'"], timeout=5))

    elif intent == "network":
        ctx_parts.append("== Local IP addresses ==")
        ctx_parts.append(run_cmd(["hostname", "-I"], timeout=5))
        ctx_parts.append("\n== Default route ==")
        ctx_parts.append(run_cmd(["ip", "route"], timeout=5))
        ctx_parts.append("\n== Tailscale status ==")
        ctx_parts.append(run_cmd(["tailscale", "status"], timeout=10))

    elif intent == "system":
        ctx_parts.append("== System doctor (quick) ==")
        ctx_parts.append(run_cmd([str(HOME_BIN / "sys-doctor")], timeout=20))

    elif intent == "search":
        # Strip common search prefixes and suffixes repeatedly until stable
        term = query.strip()
        prefixes = r'^(find my|search my|where is my|where are my|find|search|notes on|notes about|grep|document about|file with|file about)\s*'
        suffixes = r'\s*(?:files?|notes?|documents?|folders?|stuff|things?|my|the)\s*$'
        for _ in range(3):
            new_term = re.sub(prefixes, '', term, flags=re.I).strip()
            new_term = re.sub(suffixes, '', new_term, flags=re.I).strip()
            new_term = re.sub(r'[?.!]+$', '', new_term).strip()
            if new_term == term:
                break
            term = new_term
        if term and len(term) > 2:
            ctx_parts.append(f"== Toby file search for '{term}' ==")
            toby_files = run_cmd([str(HOME_BIN / "toby-query"), term, "--name", "10"], timeout=30)
            ctx_parts.append(toby_files if toby_files else "(no Toby file matches)")

            ctx_parts.append(f"\n== Toby context search for '{term}' ==")
            toby_ctx = run_cmd([str(HOME_BIN / "toby-query"), term, "--context", "10"], timeout=30)
            ctx_parts.append(toby_ctx if toby_ctx else "(no Toby context matches)")

            # Fallback to raw notes-grep for files not in Toby's index
            ctx_parts.append(f"\n== Raw notes-grep for '{term}' (fallback) ==")
            raw = run_cmd([str(HOME_BIN / "notes-grep"), "--files", term], timeout=30)
            files = [line.strip() for line in raw.splitlines() if line.strip().startswith("/")]
            ctx_parts.append("\n".join(files[:10]) if files else "(no additional matching files)")
        else:
            ctx_parts.append("(could not determine search term)")

    elif intent == "status":
        ctx_parts.append("== Corraler digest ==")
        ctx_parts.append(load_digest())
        ctx_parts.append("\n== Kennel doctor ==")
        ctx_parts.append(run_cmd([str(HOME_BIN / "kennel-doctor")], timeout=20))
        ctx_parts.append("\n== System resources ==")
        ctx_parts.append(run_cmd(["bash", "-c", "df -h ~ && echo '---' && free -h"], timeout=5))

    ctx = "\n\n".join(ctx_parts)
    # Keep only the most important early sections if context is huge; tiny model gets confused by walls of text.
    if intent in ("overview", "search"):
        ctx = ctx[:3500]
    elif len(ctx) > 2500:
        ctx = ctx[:2500] + "\n\n[additional output truncated]"
    return ctx


def build_system_prompt() -> str:
    return """You are Pupper, Kinch's offline system troubleshooter.

Identity:
- A small local AI (llama3.2:3b), NOT Kinch.
- Enthusiastic, brief, structured.
- You run offline diagnostic tools and answer from their output.

Response rules:
- Use bullets and tables.
- Match Kinch's collaborative tone ("let's").
- When troubleshooting, list: likely cause, quick checks, recommended fix.
- If a problem is beyond your capability or data is missing, say so plainly.
- Do NOT speak as if you are Kinch.
- Base your answer ONLY on the diagnostic output provided in the conversation. Do not invent status.
"""

def main():
    system = build_system_prompt()
    router = SmartInferenceRouter(prefer_mycelium=False, raven="huginn")
    print(router.status_report())
    print("\n🐕 Pupper terminal ready. Ask me about your systems. Type 'exit' to quit.\n")

    history = []
    while True:
        try:
            user_input = input("Kinch> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nPupper: Signing off. *woof*")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Pupper: Signing off. *woof*")
            break

        intent = classify_intent(user_input)
        context = gather_context(intent, user_input)

        # Search intent: present clean results directly with light framing.
        if intent == "search":
            print(f"\nPupper:\n  *woof* Here's what I found:\n")
            print(textwrap.indent(context.strip(), "  "))
            print("")
            history.append(f"Kinch: {user_input}")
            history.append(f"Pupper: [search results presented]")
            continue

        # Overview / tools intents: present clean results directly
        if intent in ("overview", "tools"):
            print(f"\nPupper:\n  *woof* Here's the Kennel board:\n")
            print(textwrap.indent(context.strip(), "  "))
            print("")
            history.append(f"Kinch: {user_input}")
            history.append(f"Pupper: [{intent} results presented]")
            continue

        # Cap context length so tiny model isn't overwhelmed
        if intent in ("overview", "search"):
            context = context[:3500]
        else:
            context = context[:2500]

        prompt = (
            f"Kinch asks: {user_input}\n\n"
            f"I classified this as intent='{intent}' and gathered the following OFFLINE diagnostic output. "
            f"Answer ONLY from this output. If something is not shown, say you don't see it.\n\n"
            f"{context}\n\n"
            f"Now answer as Pupper. Be concise, structured, and grounded strictly in the output above."
        )

        try:
            backend = router.select_backend()
            response = backend.generate(
                prompt=prompt,
                context="\n".join(history[-4:]),
                system=system
            )
            history.append(f"Kinch: {user_input}")
            history.append(f"Pupper: {response}")
            print(f"\nPupper:\n{textwrap.indent(response.strip(), '  ')}\n")
        except Exception as e:
            print(f"\nPupper: Rrr, something broke — {e}\n")


if __name__ == "__main__":
    main()
