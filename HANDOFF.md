# Handoff notes

Context for picking this work up in a new session.

## What's in this repo

- Pilot code (root): `pilot.py`, `run.py`, `tests/`, `data/`, `results/`. See `README.md`.
- `docs/course-rubric.pdf`: the course project rubric. `docs/project-proposal.pdf`: our proposal (Areesha Ashfaq, Syed Ibad Asim).
- `research/pilot-and-gemma-plan.md`: research notes on the pilot plan, competition rules and running Gemma locally.
- `partner-demo/`: partner's agent demo (`agent.py`, toy `demoRepo/`, run logs in `runs/`). See its `README.md`.
- `demo-notes/index.html`: one-page notes with both results tables for the professor demo (open in a browser).

## Project

CS/CE 351/363 AI, Fall 2026, Group 9: "Improving a Gemma 4 coding agent".
The agent: read the bug report → **(A)** search the code with keywords → edit a fix → **(B)** run tests and retry on failure (max 3).
This repo is the small pilot of step (A) that the professor asked for.

## Competitions (Kaggle)

- **Main track**: `gemma-4-developer-agent`. Deadline 2026-12-02 23:59 UTC; join/merge teams by 2026-11-25. Max team 5. Allowed models: gemma-4-31b / 12b / e4b / e2b (`-it-qat-w4a16-ct`), same model for every agent. $10k bonus for best E2B/E4B entry. The proposal's claim that only 31B is allowed is wrong.
- **Paper track**: `gemma-4-developer-agent-paper`. Deadline 2026-11-12 23:59 UTC (also last day to join). Max team 5. Writeup of at most 3,000 words. Judged on novelty, quality, relevance, verifiability and clarity.

## State of this pilot

- Results and method: see `README.md` and `results/results.md`. Headline: Gemma-picked keywords (K2) put the right file first 80% of the time, rules-only (K1) 69%, BM25 58%.
- Gemma replies are cached in `data/gemma_keywords.json`, so `python run.py --gemma` works without a GPU. New Gemma calls need the local Ollama `gemma4:12b` on the home PC (RTX 5070 Ti).
- `repos/` is not in git. Clone before running:
  ```sh
  git clone https://github.com/psf/requests repos/requests
  git clone https://github.com/pallets/flask repos/flask
  pip install datasets rank_bm25 "pytest==8.3.5"
  python -m pytest -q   # 17 tests
  python run.py --gemma
  ```
  (On the home PC use `.venv\Scripts\python`.)

## Partner's demo agent (`partner-demo/`)

A JSON-action agent (tools: listFiles, readFile, searchCode, editFile, runTests; modes baseline/search/retry/both) on a toy shop app with a planted discount bug. All 4 modes fixed it (7–10 steps, 52–78 s). Retry never triggered because the bug is easy. `--mode all` can crash Ollama (`std::bad_alloc`); workaround: `ollama stop gemma4:12b` between modes.

## Next steps

1. Held-out test: freeze the rules, run on httpx and fastapi issues (rules were tuned on these 55).
2. Better K1+K2 merge: take only the rules' code names, not plain words.
3. Reduce hub-file bias (`flask/app.py`, `requests/models.py` win too often).
4. Set up the Kaggle-exact model (`google/gemma-4-12B-it-qat-w4a16-ct`) with vLLM in WSL2.
5. Fix the proposal's 31B line; join and verify identity for both competitions.
6. Ask the RA: group of 2 OK? cross-track team membership? reuse of team code in the paper?
