# LOCALIZE_IT RAG Assistant

Train a small, offline AI that answers questions about **your** computer, **your** scripts, **your** hounds, and **your** workflow.

> *"Not the generic user manual. Your user manual."*

---

## What It Is

A retrieval-augmented generation (RAG) assistant that:
1. **Compiles** local system docs, scripts, personas, skills, and status notes into one searchable knowledge base.
2. **Retrieves** relevant snippets for each question.
3. **Answers** using a tiny local model (e.g., `llama3.2:1b`) that only uses the provided snippets.

No cloud. No API costs. Runs on CPU.

---

## Why It Fits LOCALIZE_IT

LOCALIZE_IT's goal is **personal AI sovereignty**. Fine-tuning is one path; RAG over your own artifacts is another. Both share the same capture layer:

- Explicit captures (`data/explicit/`) become **style/framework/context** entries.
- Scripts and skill docs become **reference material**.
- Daily life with the system becomes **query/answer training pairs** for the classifier.

Over time, the classifier learns which chunks you actually want for which kinds of questions.

---

## Reference Implementation

A working example lives in `examples/pupper-kb/`:

- `compile_kb.py` — compiles your local manual
- `kb_retriever.py` — retrieves snippets using the LOCALIZE_IT classifier
- `pupper_kb.py` — interactive chat with `llama3.2:1b`

Copy that directory, edit the source paths in `compile_kb.py`, and run it.

---

## Building Your Own

### 1. Gather Sources

Collect the files that describe how *you* use your machine:

```text
bin/                   # custom scripts
.pi/personas/*/        # WAKE, PERSONA, SKILL files
.pi/skills/*/          # skill definitions
Projects/kennel/       # memory/status docs
.grove-commons/        # infrastructure notes
```

### 2. Compile the Knowledge Base

A nightly script walks the sources, extracts text, chunks by section, and builds an inverted index.

Key ideas:
- **Chunk by heading**: each H2 section becomes one retrievable unit.
- **Tokenize and index**: build an inverted index of non-stopword terms.
- **Boost titles**: matches in the section title count more.
- **Snippets**: at query time, extract a short passage around the densest term matches.

### 3. Retrieve

For a question like *"What arguments does mycelium-control accept?"*:

1. Tokenize the query.
2. Look up terms in the inverted index.
3. Score chunks by term frequency, with title bonus.
4. Return the top 3–5 chunks/snippets.

### 4. Generate

Send the snippets to a local model with a strict prompt:

```text
You are a local system assistant. Answer ONLY from the snippets below.
If the answer is not in the snippets, say "I don't see that in the manual."
Do not invent commands, paths, or facts.

--- source: bin/mycelium-control ---
Usage: mycelium-control [start|stop|status|toggle-compute|toggle-api]
...

Question: What arguments does mycelium-control accept?
```

Recommended model: `llama3.2:1b` (~1.3 GB, fast on CPU).

---

## Improving the Classifier

The keyword retriever works, but it can misprioritize. LOCALIZE_IT can train a lightweight classifier that maps query types to source priorities.

### Desired KB Labels

| Label | Example Query | Priority Sources |
|:---|:---|:---|
| `TOOL_LOOKUP` | "What tools do I have?" | tinker inventory, skill docs |
| `SCRIPT_INFO` | "What arguments does X take?" | `~/bin` scripts |
| `HOUND_INFO` | "What does Shepherd do?" | persona WAKE/PERSONA files |
| `MESH_INFO` | "Is the Mycelium up?" | Grove/Mycelium status docs |
| `STATUS_REQUEST` | "What's the kennel status?" | kennel status, corraler digest |
| `LEARNING` | "How does the mesh work?" | any relevant docs |

Train the classifier by generating labeled query/answer pairs from your manual. Then use the predicted label to boost the matching source types at retrieval time.

### Training Data Sources

1. **Manual labels**: write 10–20 example queries per category.
2. **Synthetic queries**: use a larger model to generate plausible questions from each chunk.
3. **Session logs**: capture real questions you ask Pupper and label them retroactively.

Run the training script (see `src/train/train_kb_classifier.py`) and point the retriever at the new model.

---

## Maintenance

- **Daily recompile**: sources change; the KB must be rebuilt.
- **Weekly review**: check wrong answers and add better chunks or labels.
- **Keep captures clean**: LOCALIZE_IT explicit captures become first-class KB sources, so label them well.

---

## Privacy & Ownership

Everything stays local:
- Source files are on your disk.
- The index is on your disk.
- The model runs on your machine.
- No telemetry, no cloud embedding API, no rented vectors.

This is the LOCALIZE_IT charter: **your system, your model, your manual.**
