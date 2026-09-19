#!/usr/bin/env python3
"""
pupper_kb.py — Pupper in offline knowledge-base mode.

Answers questions about Kinch's system by retrieving relevant chunks from
the compiled knowledge base and running them through a small local model
(llama3.2:1b). Does NOT execute tools.

Usage:
    python3 pupper_kb.py
"""

import sys
import textwrap
from pathlib import Path
import requests

PUPPER_DIR = Path(__file__).parent


def build_system_prompt() -> str:
    return """You are Pupper, Kinch's offline knowledge-base assistant.

Identity:
- A small local AI (llama3.2:1b) running offline.
- Enthusiastic, brief, structured.
- You answer questions about Kinch's system: scripts, hounds, skills, Grove nodes, and workflows.

Response rules:
- Use bullets and short sentences.
- Match Kinch's collaborative tone: "we", "let's".
- Base your answer ONLY on the reference chunks provided by the user.
- If the answer is not in the chunks, say clearly: "I don't see that in the manual."
- Do NOT invent commands, paths, flags, or facts.
- Do NOT use outside knowledge about mycelium fungi; in this system "Mycelium" is the distributed LLM inference network.
- When listing facts, quote the source path in parentheses if the chunk has one.
- Do NOT introduce yourself or say "I'm Pupper" unless asked.
"""


def ask_ollama(question: str, context: str, model: str = "llama3.2:1b") -> str:
    """Call Ollama /api/chat directly with strict system+user messages."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {
                "role": "user",
                "content": (
                    "Below are short reference snippets from the offline system manual. "
                    "Use ONLY these snippets to answer. Do not use outside knowledge. "
                    "If the answer is not in the snippets, say 'I don't see that in the manual.'\n\n"
                    + context
                    + "\n\nQuestion: " + question
                    + "\n\nAnswer as Pupper. Be brief and structured."
                ),
            },
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.85,
            "top_k": 30,
        },
    }
    try:
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"(Ollama error: {e})"


def main():
    # Import here so the help message can print before Ollama is needed
    from kb_retriever import load_index, load_kb_classifier, retrieve_with_classifier, format_context

    print("🐕 Pupper KB mode. Loading index...")
    try:
        index = load_index()
        classifier = load_kb_classifier()
    except FileNotFoundError as e:
        print(f"Pupper: I need a knowledge base first. Run: python3 {PUPPER_DIR / 'compile_kb.py'}")
        print(f"Error: {e}")
        sys.exit(1)

    print(f"   Index loaded: {len(index['chunks'])} chunks")
    print("   Model: llama3.2:1b (offline)")
    if classifier:
        print("   Classifier: LOCALIZE_IT KB router loaded")
    else:
        print("   Classifier: not found (run compile-pupper-kb or localize_it train)")
    print("   Type your question, or 'exit' to quit.\n")

    while True:
        try:
            user_input = input("Kinch> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nPupper: Signing off. *woof*")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Pupper: Signing off. *woof*")
            break

        chunks, label = retrieve_with_classifier(user_input, index, classifier, top_k=5)
        if not chunks:
            print("\nPupper: I didn't find anything relevant in the offline manual. Try rephrasing, or run the compiler to add more sources.\n")
            continue

        context = format_context(chunks, max_chars=2800, use_snippets=True)

        response = ask_ollama(user_input, context)
        print(f"\nPupper:\n{textwrap.indent(response.strip(), '  ')}\n")


if __name__ == "__main__":
    main()
