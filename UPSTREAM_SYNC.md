# Sync to Codeberg Upstream

**Date:** 2026-06-12  
**Repository:** https://codeberg.org/kinch_kesh/localize_it

---

## What is Corraler?

**Corraler** is the Kennel's central scheduler and heartbeat system — think of it as a personal cron manager with AI awareness.

### For Users Without Corraler

If you don't have Corraler (most people won't), you can still use `localize_it` with standard cron:

```bash
# Add to your crontab instead of Corraler
0 3 * * * /path/to/localize_it/src/tier2/daily-aggregator.sh
0 9 * * 0 /path/to/localize_it/src/tier2/weekly-review.sh
```

The Corraler-specific headers in our cron scripts (like `# HOUND: localize`) are just metadata — the scripts work standalone.

---

## Summary of Changes

We took the upstream `localize_it` and added a **complete production implementation** with three tiers:

### New Files Added

#### Core CLI
- `localize` — Simple CLI (replaces complex `localize_it` command)
- `LOCALIZE_USAGE.md` — Usage guide with examples
- `PRODUCTION_SETUP.md` — Production deployment documentation

#### Tier 1: Shadow (Passive)
- `src/distill/extract-patterns.py` — Query pattern extraction
- `src/distill/analyze-style.py` — Writing style analysis
- `src/distill/build-knowledge.py` — Knowledge graph construction
- `src/distill/classify-queries.py` — Learning vs meta vs social classification
- `src/pipeline-shadow.py` — Orchestrates full pipeline

#### Tier 2: Intraday (Active)
- `src/tier2/pattern-detector.py` — Detect patterns in sessions
- `src/tier2/intraday-hook.py` — Real-time Pi integration
- `src/tier2/daily-aggregator.sh` — Daily 03:00 consolidation

#### Tier 3: Explicit (Direct)
- `src/explicit/capture-style.py` — Complete working styles
- `src/explicit/capture-framework.py` — Decision frameworks
- `src/explicit/capture-context.py` — Project contexts
- `src/explicit/capture-voice.py` — Voice/persona definitions
- `src/train/build-explicit-corpus.py` — Aggregate into corpus

#### Documentation
- Updated `README.md` with:
  - Memory Management Requirements section
  - Complete three-tier documentation
  - Simple CLI usage

---

## Key Design Decisions

1. **Simplified CLI**: Changed from `localize_it capture-style ...` to just `localize "thing"`
2. **Interactive Categorization**: The CLI asks multiple-choice questions to categorize captures
3. **Corraler Integration**: Production deployment uses Corraler (or cron) for daily 03:00 runs
4. **Memory System Agnostic**: Documented that users without Pi's Dream skill can still use it

---

## Generated Data (Not for upstream)

These files contain your personal session data and should NOT be pushed upstream:
- `data/shadow/*.json` (large pattern files)
- `data/shadow/*.md` (communication profile)
- `data/training/*.json` (training corpus)
- `data/localize/entries.jsonl` (your captures)
- `data/explicit/*/*.jsonl` (explicit captures)
- `logs/*.md` (synthesis reports)

---

## How to Sync

### Option 1: SSH Push (if you have access)

Your SSH key is set up at `~/.ssh/id_codeberg`. If authorized:

```bash
cd ~/Projects/localize_it

# Ensure SSH remote is configured
git remote set-url codeberg git@codeberg.org:kinch_kesh/localize_it.git

# Push
git push codeberg main
```

If you get "Connection closed" errors, your key may need to be added to Codeberg.

### Option 2: HTTPS with Token

```bash
# Create a personal access token on Codeberg first
# Then:
git remote set-url codeberg https://TOKEN@codeberg.org/kinch_kesh/localize_it.git
git push codeberg main
```

### Option 3: Web Interface Upload

1. Go to: https://codeberg.org/kinch_kesh/localize_it
2. Click "New File" or "Upload File" for each changed file
3. Key files to upload:
   - `localize` (the CLI script)
   - `src/distill/*.py`
   - `src/tier2/*.py`
   - `src/explicit/*.py`
   - `src/train/*.py`
   - `LOCALIZE_USAGE.md`
   - `PRODUCTION_SETUP.md`
   - Updated `README.md`

### Option 4: Create a Patch

```bash
cd ~/Projects/localize_it

# Create patch excluding generated data
git diff codeberg/main..main -- . \
  ':!data/shadow/*.json' \
  ':!data/localize/*.jsonl' \
  ':!data/training/*.json' \
  ':!data/explicit/*/*.jsonl' \
  ':!logs/*.md' \
  > ~/localize_it_production.patch

# Then upload ~/localize_it_production.patch via web interface
```

---

## What Makes This Different from Upstream

| Aspect | Upstream | Our Implementation |
|:---|:---|:---|
| CLI Complexity | Complex subcommands | Simple `localize "thing"` |
| Deployment | Manual | Corraler/cron automated |
| Pattern Detection | Conceptual | Implemented and working |
| Communication Analysis | Not included | Full profile with 21k messages |
| Production Ready | No | Yes, with monitoring |

---

## Recommendation

Consider creating a **PR** to upstream with:
1. The simplified `localize` CLI
2. The three-tier implementation scripts
3. The Corraler/cron integration pattern
4. The memory-management-agnostic documentation

Keep personal data (communication profile, session captures) private.

---

*Generated: 2026-06-12*
