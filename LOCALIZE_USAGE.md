# LOCALIZE — Usage Guide

## Simple Concept

`localize` takes anything you want to remember and asks a few questions to categorize it properly.

## Usage

```bash
# Interactive mode (asks questions)
localize "thing you want to capture"

# Quick mode (skips questions)
localize "thing" --type discovery

# Interactive mode with no arguments
localize
> (type your entry)

# List recent captures
localize --list

# Show status
localize --status
```

## Examples

### Example 1: Discovery

```
$ localize "I need to shift priorities towards job hunting"

============================================================
LOCALIZE: "I need to shift priorities towards job hunting"
============================================================

What would you call this?
  [1] A preference (how I like things)
  [2] A pattern (something I do repeatedly)
  [3] A framework (how I approach decisions)
  [4] A context (project/situation specific)
  [5] A discovery (something I just realized)
  [6] Research (information I gathered)
  [7] Just a note (capture for later)
  [c] Custom (type your own)
  [s] Skip

Select: 5

What kind of discovery?
  [1] Priority shift (changing focus)
  [2] Insight (new understanding)
  [3] Decision (made a choice)
  [4] Problem identified
  [5] Solution found
  [c] Custom
  [s] Skip

Select: 1

Add tags (comma-separated, or press Enter to skip):
Tags: job-hunting, priority

✓ Localized as: discovery
  Subcategory: Priority shift (changing focus)
  Tags: job-hunting, priority
  Saved to: data/localize/entries.jsonl

💡 This looks like a priority shift.
Want to create an action item?
  [1] Yes, create TODO
  [2] No, just capture

Select: 1
```

### Example 2: Preference

```
$ localize "I prefer code examples before explanations"

What would you call this? [1-7]: 1

What kind of preference?
  [1] Output format (how I want info presented)
  [2] Communication style (how I interact)
  [3] Technical (tools, languages, approaches)
  [4] Workflow (how I work)
  [5] General

Select: 1

✓ Localized as: preference
  Subcategory: Output format
```

### Example 3: Context

```
$ localize "the research we've done on ESP-NOW"

What would you call this? [1-7]: 4

What context is this for?
  [1] Current project/work
  [2] General setup/tools
  [3] Personal/life
  [4] Specific domain

Select: 1
Project name: DOMM

✓ Localized as: context
  Tags: project:DOMM
```

## Categories

| Category | When to Use | Examples |
|:---|:---|:---|
| **Preference** | How you like things | "I want lists not paragraphs" |
| **Pattern** | Things you do repeatedly | "I always check status first" |
| **Framework** | Decision approaches | "PEARL structure for analysis" |
| **Context** | Project/situation specific | "DOMM uses Rust + ESP-NOW" |
| **Discovery** | Realizations | "Need to pivot to job hunting" |
| **Research** | Information gathered | "Found 3 options for X" |
| **Note** | General capture | "Remember to check Y" |

## Data Flow

```
Your Input → Categorization Questions → Stored By Type
                                              ↓
                                    ┌─────────┼─────────┐
                                    ↓         ↓         ↓
                              Preferences  Patterns  Contexts
                              (intraday)   (intraday)  (explicit)
                                    ↓         ↓         ↓
                              Daily Aggregation (03:00)
                                    ↓
                              Training Corpus
                                    ↓
                              LoRA Fine-tuning
```

## RAG Assistant Mode

LOCALIZE_IT also supports a **local RAG assistant** for answering questions about your system. The same explicit captures and source docs that feed LoRA training can feed a searchable knowledge base served by a tiny local model.

See [`docs/rag-assistant.md`](docs/rag-assistant.md) for the full guide, including:
- How to compile your scripts, personas, and skills into a KB
- How to retrieve and generate answers with `llama3.2:1b`
- How to train a KB-specific query classifier
- Reference implementation in `~/.pi/personas/pupper/`

Quick start:
```bash
pupper-kb          # interactive offline KB assistant
compile-pupper-kb  # rebuild the manual now
```

---

## Integration with Shepherd

When you say **"let's localize this"** during a session, Shepherd will:

1. Identify what you want to capture
2. Run `localize [summary]`
3. Route to appropriate questions
4. Store for 03:00 daily aggregation

## Files

- `data/localize/entries.jsonl` — All entries
- `data/intraday/*.jsonl` — Tier 2 captures
- `data/explicit/*/` — Tier 3 captures
- Daily summary: `data/intraday/daily/summary-YYYY-MM-DD.md`
