# Architecture

## System Overview

```
┌──────────────┐     Usage      ┌──────────────┐
│  Cloud AI    │ ◄────────────► │     User     │
│ (Claude,     │                │              │
│  GPT, etc)   │                │              │
└──────┬───────┘                └──────┬───────┘
       │                                │
       │ Queries + Responses            │
       │ (User owns this)               │
       ▼                                ▼
┌──────────────────────────────────────────────┐
│         LOCALIZE_IT CAPTURE LAYER          │
│                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │  Shadow  │ │ Intraday │ │ Explicit │     │
│  │  Study   │ │ Logging  │ │ Commands │     │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘     │
│       │            │            │           │
│       └────────────┴────────────┘           │
│                    │                         │
│                    ▼                         │
│  ┌────────────────────────────────────┐     │
│  │      KNOWLEDGE DISTILLATION        │     │
│  │  • Filter high-value               │     │
│  │  • Extract patterns                │     │
│  │  • Synthesize training corpus      │     │
│  └───────────────────┬────────────────┘     │
└──────────────────────┼─────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│         LOCAL MODEL TRAINING (Nightly)       │
│  • LoRA/QLoRA fine-tuning                    │
│  • Incremental updates                       │
│  • No catastrophic forgetting              │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              YOUR LOCAL MODEL              │
│         (Owned. Portable. Sovereign.)        │
└──────────────────────────────────────────────┘
```

## Data Flow

### Tier 1: Shadow Study

```
Cloud Interaction → Logger → Raw Storage → Distiller → Training Corpus
```

**Components:**
- `shadow-logger.sh` — Background capture
- Raw storage: JSONL files
- Distiller: Pattern extraction scripts
- Output: Filtered training data

### Tier 2: Intraday Logging

```
Interaction → Pattern Detection → User Confirmation → Preference Store
```

**Components:**
- `intraday-prompt.py` — Active detection
- Heuristics for pattern recognition
- User prompt for confirmation
- Append-only JSONL storage

### Tier 3: Explicit Commands

```
User Command → Validation → Structured Storage → Version Control
```

**Components:**
- `explicit-cmd.sh` — Command interface
- YAML/Markdown output
- Git version control
- Framework inheritance

## Storage Layer

### Directory Structure

```
data/
├── raw/           # Original cloud interactions
│   └── YYYY-MM/
├── shadow/        # Distilled data
│   ├── style/
│   ├── patterns/
│   └── knowledge/
├── intraday/      # Active preferences
│   ├── preferences.jsonl
│   ├── patterns.jsonl
│   └── frameworks.jsonl
└── explicit/      # Command captures
    ├── styles/
    ├── frameworks/
    ├── contexts/
    └── voices/
```

### File Formats

**Raw Data:** JSONL (one JSON object per line)
```json
{"timestamp": "2024-06-10T14:30:00Z", "query": "...", "response": "...", "metadata": {...}}
```

**Intraday:** JSONL with category tags
```json
{"timestamp": "...", "preference": "...", "category": "format", "confidence": 95}
```

**Explicit:** YAML frontmatter + Markdown
```yaml
---
name: "technical-writing"
type: style
captured: 2024-06-10T14:30:00Z
---
# Style: technical-writing
...
```

## Training Pipeline

### Step 1: Corpus Preparation

```python
# pseudocode
def prepare_corpus():
    shadow_data = load_shadow_distillations()
    intraday_prefs = load_preferences()
    explicit_frameworks = load_explicit_captures()
    
    training_data = merge(shadow_data, intraday_prefs, explicit_frameworks)
    training_data = deduplicate(training_data)
    training_data = quality_filter(training_data)
    
    save_to_jsonl(training_data, "ready/corpus.jsonl")
```

### Step 2: LoRA Fine-tuning

```python
# pseudocode
def train_lora():
    base_model = load("gemma4:12b")  # or llama3.1, mistral, etc.
    corpus = load("ready/corpus.jsonl")
    
    config = LoRAConfig(
        r=64,                    # Rank
        lora_alpha=128,        # Scaling
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
    )
    
    model = get_peft_model(base_model, config)
    
    trainer = Trainer(
        model=model,
        train_dataset=corpus,
        # ... training arguments
    )
    
    trainer.train()
    save_pretrained("models/adapters/shadow-v{version}")
```

### Step 3: Model Serving

```bash
# Merge adapter with base
ollama create localize_it/shadow-v1 \
  --base gemma4:12b \
  --adapter models/adapters/shadow-v1.bin

# Serve
ollama run localize_it/shadow-v1
```

## Security Model

### Threat: Data Exfiltration

**Mitigation:** Airgap capability
- No external network calls in core
- Optional encryption at rest
- User controls all egress

### Threat: Model Theft

**Mitigation:** Physical security
- Weights stored locally
- Optional encryption
- User controls access

### Threat: Catastrophic Forgetting

**Mitigation:** Version control
- Git history of all adapters
- Rollback capability
- Temporal tagging

## Performance Considerations

### Memory Usage

| Model Size | Base RAM | With QLoRA | Context |
|:-----------|:---------|:-----------|:--------|
| 1B (Pupper) | 500MB | 600MB | 4K |
| 7B | 4GB | 5GB | 8K |
| 12B (Toby) | 8GB | 10GB | 128K |
| 70B | 40GB | N/A | 128K |

### Training Time

| Data Size | GPU | Time |
|:----------|:----|:-----|
| 1MB | RTX 4090 | 10 min |
| 10MB | RTX 4090 | 2 hours |
| 100MB | A100 | 6 hours |
| 1GB | A100 | 24 hours |

(CPU training: 10-50x slower)

## Extension Points

### Custom Capturers

Implement `CaptureInterface`:
```python
class CustomCapture:
    def start(self): ...
    def stop(self): ...
    def process(self, interaction): ...
```

### Custom Distillers

Implement `DistillInterface`:
```python
class CustomDistiller:
    def extract_patterns(self, data): ...
    def synthesize(self, patterns): ...
```

### Custom Trainers

Implement `TrainInterface`:
```python
class CustomTrainer:
    def prepare(self, corpus): ...
    def train(self, config): ...
    def export(self, path): ...
```

---

*Architecture evolves with implementation.*
