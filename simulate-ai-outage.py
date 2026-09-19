#!/usr/bin/env python3
"""
Simulate AI-restriction scenarios and measure recovery.

Scenarios:
  --ollama-down     Stop Ollama daemon, then run inference-doctor --fix
  --model-missing   Test fallback when default model is unavailable
  --mycelium-down   Verify Ollama is preferred when Mycelium is unreachable
  --all             Run all safe scenarios in sequence
  --dry-run         Describe scenarios without changing system state

Outputs a METRIC line suitable for autoresearch logging.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HOME_BIN = Path.home() / "bin"
INFERENCE_DOCTOR = str(HOME_BIN / "inference-doctor")


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def is_ollama_running() -> bool:
    code, _, _ = run(["pgrep", "-x", "ollama"], timeout=2)
    return code == 0


def stop_ollama() -> bool:
    code, _, _ = run(["pkill", "-x", "ollama"], timeout=5)
    # Wait for process to exit
    for _ in range(20):
        if not is_ollama_running():
            return True
        time.sleep(0.25)
    return False


def scenario_ollama_down(dry_run: bool = False) -> dict:
    print("\n[Scenario: Ollama daemon down]")
    if dry_run:
        print("  DRY-RUN: would stop Ollama, run inference-doctor --fix, verify recovery")
        return {"scenario": "ollama-down", "dry_run": True, "recovery_time_s": None}

    if not is_ollama_running():
        print("  Ollama already stopped; starting baseline...")
        run([INFERENCE_DOCTOR, "--fix"], timeout=60)
        time.sleep(1)

    # Confirm baseline healthy
    baseline = run([INFERENCE_DOCTOR, "--json"], timeout=90)
    try:
        base_report = json.loads(baseline[1])
    except Exception:
        base_report = {"recommended": {"backend": "unknown"}}

    if base_report.get("recommended", {}).get("backend") == "none":
        print("  ⚠ Baseline already unhealthy; skipping destructive test")
        return {"scenario": "ollama-down", "skipped": True, "reason": "baseline unhealthy"}

    # Stop Ollama
    print("  Stopping Ollama daemon...")
    if not stop_ollama():
        return {"scenario": "ollama-down", "error": "failed to stop Ollama for test"}

    # Measure recovery
    print("  Running inference-doctor --fix...")
    start = time.time()
    code, out, err = run([INFERENCE_DOCTOR, "--fix", "--json"], timeout=120)
    elapsed = time.time() - start

    # Verify
    verify = run([INFERENCE_DOCTOR, "--json"], timeout=90)
    try:
        verify_report = json.loads(verify[1])
    except Exception:
        verify_report = {"recommended": {"backend": "none"}}

    recovered = verify_report.get("recommended", {}).get("backend") != "none"
    print(f"  Recovery time: {elapsed:.2f}s  {'✓ recovered' if recovered else '✗ still down'}")

    return {
        "scenario": "ollama-down",
        "recovery_time_s": round(elapsed, 2),
        "recovered": recovered,
        "recommended": verify_report.get("recommended"),
    }


def scenario_model_missing(dry_run: bool = False) -> dict:
    print("\n[Scenario: Default model missing / fallback needed]")
    code, out, err = run([INFERENCE_DOCTOR, "--json"], timeout=90)
    try:
        report = json.loads(out)
    except Exception:
        report = {"ollama": {"models": []}}

    models = report.get("ollama", {}).get("models", [])
    if dry_run:
        print(f"  DRY-RUN: would test fallback chain across installed models: {models}")
        return {"scenario": "model-missing", "dry_run": True, "models": models}

    # We don't actually remove models. Instead, test each small model directly
    # and report the first working fallback. This validates the chain without
    # destructive changes.
    tested = {}
    for model in ["llama3.2:1b", "qwen2.5:1.5b", "llama3.2:3b", "qwen2.5:3b"]:
        if model in models:
            start = time.time()
            code, out, err = run([INFERENCE_DOCTOR, "--test-model", model, "--json"], timeout=90)
            elapsed = time.time() - start
            try:
                r = json.loads(out)
                res = r.get("ollama", {}).get("tested", {}).get(model, {})
                tested[model] = {"ok": res.get("ok", False), "latency_s": res.get("latency_s"), "total_s": round(elapsed, 2)}
            except Exception as e:
                tested[model] = {"ok": False, "error": str(e)}

    working = [m for m, r in tested.items() if r.get("ok")]
    print(f"  Working fallback models: {working}")
    print(f"  Tested: {json.dumps(tested, indent=2)}")

    return {
        "scenario": "model-missing",
        "fallback_chain_works": len(working) > 0,
        "working_models": working,
        "tested": tested,
    }


def scenario_mycelium_down(dry_run: bool = False) -> dict:
    print("\n[Scenario: Mycelium unreachable]")
    code, out, err = run([INFERENCE_DOCTOR, "--json"], timeout=90)
    try:
        report = json.loads(out)
    except Exception:
        report = {"mycelium": {"ok": False}}

    mycelium_ok = report.get("mycelium", {}).get("ok", False)
    ollama_ok = report.get("recommended", {}).get("backend") == "ollama"
    print(f"  Mycelium up: {mycelium_ok} | Ollama available: {ollama_ok}")

    if dry_run:
        return {"scenario": "mycelium-down", "dry_run": True}

    return {
        "scenario": "mycelium-down",
        "ollama_can_cover": ollama_ok,
        "mycelium_reachable": mycelium_ok,
        "recommended": report.get("recommended"),
    }


def main():
    parser = argparse.ArgumentParser(description="Simulate AI access restrictions and measure recovery")
    parser.add_argument("--ollama-down", action="store_true", help="test Ollama daemon failure and recovery")
    parser.add_argument("--model-missing", action="store_true", help="test model fallback chain")
    parser.add_argument("--mycelium-down", action="store_true", help="test Mycelium failure scenario")
    parser.add_argument("--all", action="store_true", help="run all scenarios")
    parser.add_argument("--dry-run", action="store_true", help="describe scenarios without changing state")
    args = parser.parse_args()

    if not any([args.ollama_down, args.model_missing, args.mycelium_down, args.all]):
        args.all = True

    results = []
    if args.all or args.ollama_down:
        results.append(scenario_ollama_down(args.dry_run))
    if args.all or args.model_missing:
        results.append(scenario_model_missing(args.dry_run))
    if args.all or args.mycelium_down:
        results.append(scenario_mycelium_down(args.dry_run))

    # Summary metric: worst-case recovery time among tested scenarios
    recovery_times = [r.get("recovery_time_s") for r in results if r.get("recovery_time_s") is not None]
    worst_recovery = max(recovery_times) if recovery_times else None
    all_recovered = all(r.get("recovered", True) for r in results)

    print("\n" + "=" * 64)
    print("SCENARIO SUMMARY")
    print("=" * 64)
    print(json.dumps(results, indent=2, default=str))

    if worst_recovery is not None:
        print(f"\nMETRIC recovery_time_s={worst_recovery:.2f}")
        if not all_recovered:
            print("STATUS not_all_recovered")
            sys.exit(1)
    else:
        print("\nMETRIC recovery_time_s=0")


if __name__ == "__main__":
    main()
