# DEPLOYMENT CAUTION — LOCALIZE_IT Learning Layer

**Date:** 2026-10-05  
**Author:** Shepherd  
**Status:** Active constraint

---

## Do not touch these without explicit operator/human approval

| Service | Port | Why it is protected |
|---|---|---|
| Mycelium API gateway | `11435` | Live inference router; cloud model and local models depend on it |
| Ollama | `11434` | Local model host; current session uses it |
| Mycelium compute RPC | `50052` | Running compute node on this machine |
| Tailscale / Syncthing | — | Mesh connectivity for all Grove nodes |

## What is safe to edit

| File / Area | Safe? |
|---|---|
| `mycelium-library/localize-it-corpus/*.md` | ✅ Static corpus files |
| `src/router/capture_router.py` | ✅ Prototype script, not running |
| `grove-commons/STATUS/*` | ✅ Shared documentation |
| `persona_prefix.md` | ✅ Static file, not yet injected |
| Gateway integration code | ⏸ Only after reviewed deployment plan |
| `digest_watcher.py` | ⏸ Only after reviewed deployment plan |

## Deployment rule

Any change that could affect live inference must be:
1. Reviewed by the operator/human
2. Tested on a non-production node first
3. Rolled back automatically if the gateway health check fails

---

*The mesh is fragile right now. We build carefully.*
