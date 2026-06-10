# API Reference

## Master Command

### `localize_it`

Main entry point for all operations.

```bash
localize_it [command] [options]
```

---

## Shadow Tier Commands

### `shadow-start`

Begin passive capture of cloud AI interactions.

```bash
localize_it shadow-start
```

**Description:** Starts background process that monitors for cloud AI interactions and logs them to `data/raw/`.

**Output:**
- PID file: `/tmp/localize_it-shadow.pid`
- Logs: `data/raw/YYYY-MM/`

---

### `shadow-stop`

End passive capture.

```bash
localize_it shadow-stop
```

**Description:** Stops the shadow logger process.

---

### `shadow-status`

Check capture status.

```bash
localize_it shadow-status
```

**Output:**
- Running status
- Data volume captured
- Last capture time

---

### `shadow-process`

Process yesterday's data.

```bash
localize_it shadow-process
```

**Description:**
1. Collects yesterday's interactions
2. Extracts patterns
3. Analyzes style
4. Builds knowledge graph
5. Generates synthesis report

**Output:**
- `data/shadow/patterns/YYYYMMDD.json`
- `data/shadow/style/YYYYMMDD.json`
- `data/shadow/knowledge/YYYYMMDD.json`
- `logs/shadow-synthesis-YYYYMMDD.md`

---

### `train-nightly`

Run LoRA training.

```bash
localize_it train-nightly [options]

Options:
  --date=YYYY-MM-DD    Process specific date (default: yesterday)
  --adapter-size=64    LoRA rank (default: 64)
  --quantize=q4_0      Quantization (q4_0, q4_k_m, q8_0)
```

**Description:** Trains a LoRA adapter on processed shadow data.

**Output:**
- `models/adapters/shadow-v{N}.bin`
- Training logs

---

## Intraday Tier Commands

### `note-preference`

Capture explicit preference.

```bash
localize_it note-preference "preference text"
```

**Example:**
```bash
localize_it note-preference "I always prefer bullet points over paragraphs"
```

**Storage:** `data/intraday/preferences.jsonl`

---

### `note-pattern`

Capture detected pattern.

```bash
localize_it note-pattern "pattern description" [--type=behavior]
```

**Example:**
```bash
localize_it note-pattern "Asks for examples after abstract explanations" --type=learning
```

**Storage:** `data/intraday/patterns.jsonl`

---

### `ask-preference`

Interactive preference detection.

```bash
localize_it ask-preference "detected pattern"
```

**Description:** Prompts user to confirm/refine a detected pattern.

---

### `intraday-stats`

Show preference statistics.

```bash
localize_it intraday-stats
```

**Output:**
- Total preferences
- By category
- Total patterns
- Recent frameworks

---

## Explicit Tier Commands

### `capture-style`

Capture working style.

```bash
localize_it capture-style [options]

Options:
  --name="style-name"           Required. Style identifier
  --description="..."           Required. Style description
  --examples="/path/to/dir"     Optional. Example files
  --rules="rule1; rule2"        Optional. Style rules
```

**Example:**
```bash
localize_it capture-style \
  --name="technical-docs" \
  --description="Concise, code-first, assumes reader knows basics" \
  --rules="Never use 'utilize'; Always use 'use'"
```

**Output:** `data/explicit/styles/style-name.md`

---

### `capture-framework`

Capture decision framework.

```bash
localize_it capture-framework [options]

Options:
  --name="framework-name"       Required. Framework identifier
  --description="..."         Optional. Framework purpose
  --steps="step1,step2,..."   Required. Comma-separated steps
  --criteria="crit1,crit2"      Optional. Evaluation criteria
```

**Example:**
```bash
localize_it capture-framework \
  --name="debugging-method" \
  --description="How to debug systematically" \
  --steps="Reproduce,Isolate,Hypothesize,Test,Verify,Document"
```

**Output:** `data/explicit/frameworks/framework-name.md`

---

### `capture-context`

Capture project context.

```bash
localize_it capture-context [options]

Options:
  --project="project-name"      Required. Project identifier
  --stack="tech1,tech2"         Optional. Technology stack
  --patterns="pat1,pat2"        Optional. Architectural patterns
  --constraints="..."           Optional. Project constraints
```

**Example:**
```bash
localize_it capture-context \
  --project="localize_it" \
  --stack="Python,LoRA,JSONL" \
  --patterns="Modular,Offline-first"
```

**Output:** `data/explicit/contexts/project-name.md`

---

### `capture-voice`

Capture persona/voice.

```bash
localize_it capture-voice [options]

Options:
  --name="voice-name"           Required. Voice identifier
  --traits="trait1,trait2"      Required. Core traits
  --markers="mark1,mark2"       Optional. Speech markers
  --sample="/path/to/samples"     Optional. Training samples
```

**Example:**
```bash
localize_it capture-voice \
  --name="pupper-v2" \
  --traits="technical,enthusiastic,brief" \
  --markers="occasional-dog-metaphors"
```

**Output:** `data/explicit/voices/voice-name.md`

---

## Model Commands

### `chat`

Chat with local model.

```bash
localize_it chat [--model=model-name]
```

**Options:**
- `--model=shadow-latest` (default)
- `--model=shadow-v{N}` specific version

---

### `serve`

Start OpenAI-compatible API server.

```bash
localize_it serve [--port=11434]
```

**Endpoint:** `http://localhost:11434/v1/chat/completions`

---

### `list-models`

Show available models.

```bash
localize_it list-models
```

---

## Utility Commands

### `configure`

Initial setup.

```bash
localize_it configure [options]

Interactive prompts:
  Cloud provider (anthropic/openai/gemini)
  Capture level (minimal/standard/all)
  Auto-train time (default: 03:00)
```

**Output:** `~/.config/localize_it/config.yaml`

---

### `status`

System status.

```bash
localize_it status
```

**Output:**
- Data volumes
- Model counts
- Shadow logger status

---

### `doctor`

Health check.

```bash
localize_it doctor [--full]
```

**Checks:**
- Project structure
- Ollama service
- Base models
- Training dependencies

---

### `export-corpus`

Export training data.

```bash
localize_it export-corpus /path/to/export
```

---

### `import-corpus`

Import previous training.

```bash
localize_it import-corpus /path/to/import
```

---

## Configuration File

### Location

`~/.config/localize_it/config.yaml`

### Example

```yaml
cloud:
  provider: anthropic
  capture_level: standard

training:
  auto_train_time: "03:00"
  adapter_size: 64
  quantization: q4_0

privacy:
  encrypt_at_rest: false
  airgap_mode: false
```

---

## Exit Codes

| Code | Meaning |
|:-----|:--------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Configuration error |
| 4 | Training failure |
| 5 | Network error (if applicable) |

---

*API evolves with implementation.*
