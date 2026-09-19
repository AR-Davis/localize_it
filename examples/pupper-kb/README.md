# Pupper KB — Reference RAG Assistant

A small, offline retrieval-augmented generation (RAG) assistant that answers
questions about your personal system. It compiles local docs, scripts, and
personas into a searchable knowledge base and runs them through a tiny local
model like `llama3.2:1b`.

This is a **reference implementation** from the Kennel. Adapt the source paths
in `compile_kb.py` to match your own machine.

## Files

| File | Purpose |
|:---|:---|
| `compile_kb.py` | Walks source directories and builds `knowledge_base.md` + `knowledge_base.json` |
| `kb_retriever.py` | Loads the index, classifies queries, retrieves relevant snippets |
| `pupper_kb.py` | Interactive chat loop that calls Ollama `/api/chat` |

## Quick Start

1. Install Ollama and pull a small model:
   ```bash
   ollama pull llama3.2:1b
   ```

2. Edit `compile_kb.py` to point at your own scripts, docs, and notes.

3. Build the knowledge base:
   ```bash
   python3 compile_kb.py
   ```

4. Chat with it:
   ```bash
   python3 pupper_kb.py
   ```

## Optional: Train the KB Classifier

The retriever can load a LOCALIZE_IT classifier that maps question types to
source priorities. Train it with:

```bash
cd ~/Projects/localize_it
python3 src/train/train_kb_classifier.py
```

Then `kb_retriever.py` will automatically use `models/kb_classifier.pkl`.

## Customization

- Add more source directories in `compile_kb.py`'s `SOURCES` list.
- Adjust `HOUND_NAMES` in `kb_retriever.py` to match your own agents/personas.
- Change the model in `pupper_kb.py` from `llama3.2:1b` to whatever fits your
  hardware.

## How It Relates to LOCALIZE_IT

LOCALIZE_IT captures your preferences, patterns, and frameworks over time.
This RAG assistant gives you an immediate, offline way to query the artifacts
you already have. As the classifier improves with more labeled queries, the
retrieval becomes more personal and more accurate.
