# localize_it Capture Review — 2026-10-05

Captured items reviewed and either archived or converted below.

---

## 1. Priority Shift / Maine Monitor Deadline

**Source:** Kinch (household tier) — captured twice on 2026-10-02.
**Type:** discovery
**Original:** "I need to shift priorities toward job hunting and submit the Maine Monitor materials before October 11."
**Disposition:** Closed. Maine Monitor materials were already sent; priorities have since shifted again to the Austin Chronicle freelance contract.
**Librarian note:** Demonstrates that household-tier "discovery" captures from Kinch should be treated as live priority signals and reconciled with the current WORK_TRACKER within one session.

---

## 2. Feedback on Question Routing (RAG vs Librarian)

**Source:** Console feedback (fb-console-4c277440) — 2026-10-04.
**Prompt:** "Tell me more about how you assign questions I ask you and how you decide what goes to RAG and what goes to the librarian."
**Disposition:** Archived as a training example. The response over-relied on the "Kinch Persona Prefix" framing and did not clearly describe the actual router logic. Future classifier/librarian docs should explain:
- Household-tier user statements are routed by intent category (preference, framework, discovery, feedback, research).
- `use_rag` is set by the router; `auto_rag` is a fallback.
- The librarian handles durable, reference-style context; RAG handles immediate, answerable lookups.

---

## 3. Capability Self-Inventory Feedback

**Source:** Console feedback (fb-console-73c57804) — 2026-10-04.
**Prompt:** "List 10 of the most common things you think you can be used for."
**Response list:** Data analysis, web development, machine learning, network optimization, cybersecurity, database administration, IT support, virtual assistance, content creation, system administration.
**Disposition:** Archived. This is a useful baseline capability inventory for Pupper/offline usage and can inform a "what can the Kennel do for me?" help doc. It should be rewritten to reflect actual Shepherd/Kennel functions rather than generic IT skills.

---

## Next Steps for Mycelium Training
- [ ] Add a concise "Routing 101" note to the librarian corpus.
- [ ] Add a "Kennel capabilities" summary derived from capture #3.
- [ ] Update classifier training set with these three examples so future `feedback` captures route cleanly without generating duplicate action tasks.
