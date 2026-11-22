# Context — Learning-Path Effort

Companion to **`learning-path.md`**. Captures *why* that file exists and where things stand, so
any future session (or me) can pick up without re-deriving everything.

## What this is
A **learning path** to deeply understand the whole Gemma knowledge-distillation agent, end to end.
Goal is *understanding*, not a new innovation.

## The course project & the bar
- This is for an **AI course project**. The **prof said deep mechanistic understanding alone = full
  marks** (he knows the topic is very technical). So explaining the mechanism *is* the deliverable.
- Priority: **score full on the course project**, and separately climb the Kaggle leaderboard.

## The competition
- **Google – The Gemma 4 Developer Agent Competition** (Kaggle) — a **SWE-bench-style coding-agent
  benchmark**: agent reads a GitHub bug report, edits the repo, submits a patch, graded on hidden tests.
- User's own hand-drawn diagram captures this **grading loop** accurately.

## The key reframe (the "aha")
- User's diagram = the **outer loop** (how the agent is graded).
- User's actual project (12B teacher → E4B student via LoRA distillation) lives **inside the "our
  agent" box** — the model + how it's trained. The learning path = **zoom into that box**.

## Two scores, two levers
- **Scores:** course grade (earned by *understanding/explaining*) vs. Kaggle leaderboard (earned by a
  *trained agent solving tasks*). Same rungs serve both, differently.
- **Levers:** **Brain** = distillation + LoRA (the approved core plan). **Scaffold** = tools,
  retrieval/RAG, self-verify/retry (optional add-ons; feed the model better inputs). They stack.

## The rungs (full detail in learning-path.md)
0. Outer loop (user's diagram) — **DONE ✅**
1. Agent = a model emitting tool calls in a loop
2. Inside the model: tokens + attention
3. Small vs big (E4B vs 12B)
4. LoRA (cheap fine-tuning, fits 16 GB)
5. Distillation — teacher→student ← **user's actual work, the heart**
6. Full circle (capstone master diagram)
7. Self-improving agents (bonus/frontier)

## Resource decisions
- Learn order per rung: 🎥 video → 📖 blog/book → 📄 paper (paper = optional depth flex).
- Stanford courses added: **CS329A** (Self-Improving AI Agents, 20 lec) and **CS329Z** (Engineering
  AI Agents, Fall 2026). Full lecture tables + rung mapping in the Appendix of learning-path.md.
- 3B1B: watch **Ch 5 (Transformers) + Ch 6 (Attention)** for Rung 2 — those are the transformer
  architecture. Ch 1–4 (generic nets / gradient descent / backprop) = optional, only for Rung 4
  training intuition.

## Progress (as of 2026-11-23)
- **Rung 0: done** (diagram is the explainer artifact).
- Watched: **Andrej Karpathy "Intro to LLMs"** (→ already into Rung 1); **CS329Z #1** (Foundations).
- **Next up:** CS329Z **#4 Tool Use & Function Calling** (core of Rung 1) → **#6**; then 3B1B
  **Ch 5 → Ch 6** for Rung 2. Comp-critical later: CS329Z **#16 (SWE-bench authors)**, **#18
  (Coding Agents)**; CS329A **#13 (Agentic Frameworks for SW Eng)**.

## Open threads / decisions pending
- **RAG as a scaffold lever:** valid option (SWE-bench itself uses retrievers; user's "grep" is a
  baby retriever). Optional add-on, **after** the brain/distillation core is solid. ⚠️ Watch
  **competition-only scope**: an external embedding model may break the "official comp models only"
  rule — check the allowed embedder before building.
- Not yet started: Rungs 1–7 teaching sessions (one rung per sitting: I teach → build explainer → check off).

## Working style
- Plain language (`/bro`), show-and-teach every step, each rung outputs a small explainer for the prof.

## Related
- `learning-path.md` (the plan itself).
- Project: LoRA distillation plan (12B teacher → E4B adapter, screen set held out).
