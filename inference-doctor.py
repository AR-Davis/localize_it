#!/usr/bin/env python3
"""
Inference Doctor — diagnose and recover local AI inference backends.

Checks (in order of preference):
  1. Local Ollama daemon + installed models
  2. Mycelium distributed mesh API
  3. Fallback models (smallest first) if the default model fails

Usage:
  inference-doctor                human-readable report
  inference-doctor --json         machine-readable report
  inference-doctor --fix          auto-start Ollama / Mycelium if down
  inference-doctor --test-model MODEL   test one specific model
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

OLLAMA_ENDPOINT = "http://localhost:11434"
MYCELIUM_ENDPOINT = "http://localhost:11435"
TEST_PROMPT = "Say 'inference online' and nothing else."
PREFERRED_MODELS = ["llama3.2:3b", "qwen2.5:3b", "qwen2.5:1.5b", "llama3.2:1b"]
SMALL_MODELS = ["llama3.2:1b", "qwen2.5:1.5b", "llama3.2:3b", "qwen2.5:3b"]


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def ollama_daemon_running() -> bool:
    code, _, _ = run(["pgrep", "-x", "ollama"], timeout=2)
    return code == 0


def start_ollama() -> bool:
    code, out, err = run(["ollama", "serve"], timeout=5)
    # ollama serve usually stays running, so timeout is expected if it started
    if "address already in use" in (err + out).lower():
        return True
    # Give it a moment to bind
    for _ in range(10):
        if ollama_daemon_running():
            return True
        time.sleep(0.5)
    return False


def list_ollama_models() -> list[str]:
    code, out, err = run(["ollama", "list"], timeout=10)
    if code != 0:
        return []
    models = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def test_ollama_model(model: str, timeout: int = 45) -> dict:
    start = time.time()
    payload = {
        "model": model,
        "prompt": TEST_PROMPT,
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 0.9, "top_k": 40},
    }
    try:
        import requests
        r = requests.post(f"{OLLAMA_ENDPOINT}/api/generate", json=payload, timeout=timeout)
        elapsed = time.time() - start
        if r.status_code == 200:
            text = r.json().get("response", "").strip()
            return {"ok": True, "latency_s": round(elapsed, 2), "sample": text[:80]}
        else:
            return {"ok": False, "latency_s": round(elapsed, 2), "error": f"HTTP {r.status_code}"}
    except Exception as e:
        elapsed = time.time() - start
        return {"ok": False, "latency_s": round(elapsed, 2), "error": str(e)}


def check_mycelium() -> dict:
    try:
        import requests
        start = time.time()
        r = requests.get(f"{MYCELIUM_ENDPOINT}/api/status", timeout=3)
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            nodes = [n.get("name") for n in data.get("nodes", []) if n.get("status") == "healthy"]
            return {"ok": True, "latency_s": round(elapsed, 3), "nodes": nodes, "details": data}
        return {"ok": False, "latency_s": round(elapsed, 3), "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "latency_s": None, "error": str(e)}


def find_working_model(models: list[str], candidates: list[str]) -> Optional[tuple[str, dict]]:
    for model in candidates:
        if model in models:
            result = test_ollama_model(model)
            if result["ok"]:
                return model, result
    return None


def diagnose(fix: bool = False, test_model: Optional[str] = None) -> dict:
    report = {"timestamp": time.time(), "ollama": {}, "mycelium": {}, "recommended": None, "fixes": []}

    # Ollama daemon
    daemon_ok = ollama_daemon_running()
    report["ollama"]["daemon"] = daemon_ok
    if not daemon_ok:
        if fix:
            if start_ollama():
                report["fixes"].append("started ollama daemon")
                daemon_ok = True
            else:
                report["fixes"].append("failed to start ollama daemon")
        else:
            report["fixes"].append("run: ollama serve")

    # Ollama models
    models = []
    if daemon_ok:
        models = list_ollama_models()
    report["ollama"]["models"] = models

    # Test model(s)
    if test_model:
        report["ollama"]["tested"] = {test_model: test_ollama_model(test_model)}
    else:
        tested = {}
        working = None
        # First, try preferred default
        for m in PREFERRED_MODELS:
            if m in models and m not in tested:
                tested[m] = test_ollama_model(m)
                if tested[m]["ok"] and not working:
                    working = (m, tested[m])
                    break
        # If no preferred works, try all installed models
        if not working:
            working = find_working_model(models, SMALL_MODELS)
            if working:
                m, res = working
                tested[m] = res
        # Fill in remaining untested models lightly
        for m in models:
            if m not in tested:
                tested[m] = {"installed": True, "tested": False}
        report["ollama"]["tested"] = tested
        if working:
            report["recommended"] = {"backend": "ollama", "model": working[0], "latency_s": working[1]["latency_s"]}

    # Mycelium
    mycelium = check_mycelium()
    report["mycelium"] = mycelium
    if mycelium["ok"] and not report["recommended"]:
        report["recommended"] = {"backend": "mycelium", "model": "llama3.2:1b", "latency_s": mycelium["latency_s"]}
    elif mycelium["ok"] and report["recommended"] and report["recommended"]["backend"] == "ollama":
        # Keep Ollama preferred for local reliability, but note Mycelium is up
        pass

    if not report["recommended"]:
        if not models:
            report["recommended"] = {"backend": "none", "model": None, "error": "no local models installed"}
        else:
            report["recommended"] = {"backend": "none", "model": None, "error": "models installed but none responded to test prompt"}

    return report


def print_report(report: dict):
    rec = report["recommended"]
    print("🧠 INFERENCE DOCTOR")
    print("═══════════════════════════════════════════════════════════════")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report['timestamp']))}")
    print()

    print("━━━ Ollama ━━━")
    daemon = "✓ running" if report["ollama"].get("daemon") else "✗ not running"
    print(f"  Daemon: {daemon}")
    if report["ollama"].get("models"):
        print(f"  Models installed: {', '.join(report['ollama']['models'])}")
    else:
        print("  Models installed: none")

    tested = report["ollama"].get("tested", {})
    if tested:
        print("  Tested:")
        for model, res in tested.items():
            if "ok" in res:
                status = f"✓ {res['latency_s']}s" if res["ok"] else f"✗ {res.get('error', 'failed')}"
                print(f"    {model}: {status}")
            else:
                print(f"    {model}: installed (not tested)")
    print()

    print("━━━ Mycelium ━━━")
    if report["mycelium"].get("ok"):
        nodes = report["mycelium"].get("nodes", [])
        print(f"  ✓ API responsive ({report['mycelium']['latency_s']}s)")
        print(f"  Healthy nodes: {', '.join(nodes) if nodes else 'none'}")
    else:
        err = report["mycelium"].get("error", "unreachable")
        print(f"  ✗ API unreachable ({err})")
    print()

    print("━━━ Recommendation ━━━")
    if rec["backend"] == "ollama":
        print(f"  🟢 Use Ollama model: {rec['model']} ({rec['latency_s']}s test latency)")
    elif rec["backend"] == "mycelium":
        print(f"  🟡 Use Mycelium fallback ({rec['latency_s']}s API latency)")
    else:
        print(f"  🔴 No working backend: {rec.get('error', 'unknown failure')}")
    print()

    if report["fixes"]:
        print("━━━ Fixes applied ━━━")
        for fix in report["fixes"]:
            print(f"  • {fix}")
        print()

    if rec["backend"] == "none":
        print("Recovery commands:")
        print("  ollama serve                              # start local server")
        print("  ollama pull llama3.2:3b                   # download default model (needs net)")
        print("  mycelium-control start                    # start distributed mesh node")
        print()


def main():
    parser = argparse.ArgumentParser(description="Diagnose and recover local AI inference")
    parser.add_argument("--json", action="store_true", help="output JSON report")
    parser.add_argument("--fix", action="store_true", help="auto-start services if possible")
    parser.add_argument("--test-model", help="test a specific Ollama model")
    args = parser.parse_args()

    report = diagnose(fix=args.fix, test_model=args.test_model)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(report)

    rec = report["recommended"]
    if rec["backend"] == "none":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
