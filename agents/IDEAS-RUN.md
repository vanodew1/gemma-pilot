# Ideas run (autonomous, started 2026-11-02)

The one output file for the autonomous "find better ideas" run. Everything done in the run is recorded here.

## Catch-up prompt (paste on the laptop)

> Read agents/IDEAS-RUN.md top to bottom, then agents/PROJECT-BRIEF.md and agents/SESSION-HANDOFF.md. Summarise in plain words what the autonomous run found, which idea it recommends, what was actually tested and what numbers came out, then continue the grilling session from the open questions at the end of IDEAS-RUN.md.

## Context at start of run

- **Project:** Group 9 (Syed Ibad Asim, Areesha Ashfaq). Kaggle "Gemma 4 Developer Agent" main track (Dec 2) plus the Paper Track (Nov 12). Goal: course grade is the floor; win a paper-track prize; stretch goal is the E4B $10k small-model bonus.
- **Hard rules:**
  - Only official competition rules, models and data.
  - The user and partner write all prose.
  - Push only as `vanodew1`, with no Claude attribution in commits.
- **Paper plan before this run:**
  - Question: where does each Gemma size (E2B, E4B, 12B) break as the search-word picker for file localization, and which cheap fixes recover it?
  - Fixes to test: voting, code-name merge, forced JSON, 3-shot.
  - Data: the 129 competition dev tasks.
- **Competition data:** not downloaded yet; it needs the user's Kaggle identity verification and a `kaggle.json` token. Until then, the only runnable data is the 55 old SWE-bench pilot issues. They're for **code checks and early signals only, never paper numbers.**
- **Pilot results on the 55 issues:**
  - Hit@1: 12B 80, E4B 69, E2B 71, rules 69, BM25 58.
  - Hit@3: 12B 93, E4B 85, E2B 80.
- **Machine:** RTX 5070 Ti 16 GB. Ollama models: gemma4:12b, e4b, e2b. WSL2 and Docker are installed.

## Run log

_(filled in as the run goes)_
