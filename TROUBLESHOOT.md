# Pupper Offline Troubleshooter — Status

## What We Found

Kinch was right — a rich offline tool ecosystem already exists. It just wasn't wired into Pupper.

### Existing Offline Tools (all in `~/bin/`)

| Tool | Purpose | Used by Pupper? |
|:---|:---|:---:|
| `sys-doctor [quick\|full]` | System health: disk, memory, services, network, security | ✅ |
| `kennel-doctor` | Kennel-specific health: Ollama models, personas, Toby reports | ✅ |
| `kennel-offline-mode` | Test airgap capability | ⏸ |
| `notes-grep <term>` | Search local notes across Desktop/Docs/Projects/.pi/Sync | ✅ |
| `file-find-smart` | Content-aware file finder | ⏸ |
| `docs-search <topic>` | Search local docs/man pages | ⏸ |
| `mycelium-control` | Start/stop Shepherd's Mycelium node | ⏸ |
| `grove-offline` | Grove offline tool menu | ⏸ |
| `khelp` | List all 40+ custom commands | ⏸ |
| `toby "query"` | Deep offline research (Gemma 4 12B) | ⏸ |
| `ai-ask <question>` | Generic local Ollama query | ⏸ |
| `case-status` | Show active case work | ⏸ |
| `budger-watch` | Trading bot/portfolio status | ✅ |

### Existing Personas

| Persona | Role | Offline? |
|:---|:---|:---:|
| **Pupper** | Quick offline companion | ✅ |
| **Toby** | Deep research / file archivist | ✅ (but index not built) |
| **Builder** | Offline mesh/connectivity architect | ✅ |
| **Tinker** | Tool inventory / access line awareness | ✅ |
| **Corraler** | Scheduling / heartbeat | hybrid |

### localize_it

Already built and trained:
- `localize` CLI for capturing preferences/patterns/contexts
- `src/inference/predict.py` — query classifier (models exist)
- `src/distill/classify-queries.py` — rule-based query classifier
- Daily aggregator, pattern detector, corpus builder

## What I Just Did

Rewrote `pupper_terminal.py` so Pupper can act as a natural-language dispatcher:

1. **Classifies intent** from your query (mesh / kennel / trading / network / system / search / status / general).
2. **Runs the right offline tools** via subprocess:
   - `tailscale status` + RPC port probes for mesh
   - `kennel-doctor` + Corraler digest for kennel status
   - `budger-watch` + trader logs for trading
   - `sys-doctor` for system health
   - `notes-grep` for file search
3. **Feeds tool output into the local LLM** (`llama3.2:3b`) with a strict "answer only from this output" prompt.
4. **Presents structured answers** as Pupper.

Search queries bypass the LLM and show clean file + matching-line results directly.

## Current Capabilities

- ✅ "Is the Mycelium mesh up?" → runs Tailscale + RPC probes, reports live status
- ✅ "Status report!" → Corraler digest + kennel-doctor summary
- ✅ "Find my notes on X" → `notes-grep` results
- ✅ "Why isn't my trading bot trading?" → `budger-watch` + log tail
- ✅ "Check my network" → IPs, routes, Tailscale status

## Model Decision

After benchmarking 4 local models, the default Pupper brain is now **llama3.2:3b**:
- Better formatting (tables, bullets)
- More grounded answers
- Consistent ~13s latency
- 2 GB RAM footprint is acceptable here

Other models remain available:
- `qwen2.5:1.5b` — lighter fallback
- `qwen2.5:3b` — slower but deeper reasoning
- `llama3.2:1b` — original baseline

## Limitations

1. **Context window:** Tool output is capped at ~2500 chars before the model gets confused.
2. **Toby's index is not built:** `~/.pi/personas/toby/local_index.db` does not exist.
3. **Intent routing is regex-based**, not using the trained `localize_it` classifier yet.

## Recommended Next Steps (Phase 2+)

1. **Build Toby's index** so Pupper can ask Toby for deep file recall
2. **Use `localize_it`'s trained classifier** for intent routing
3. **Add more tool integrations:** `mycelium-control status`, `case-status`, `tinker-check`, `grove-offline`

## How to Run Pupper

```bash
cd ~/.pi/personas/pupper && python3 pupper_terminal.py
```
