# Session handoff (2026-11-02)

How to continue this Claude Code session on another machine. Read this, then `PROJECT-BRIEF.md` (decisions, rules, paper plan) and `sources/` (cited details).

## Resume prompt

Paste this into a new Claude Code session opened in the cloned `gemma-pilot` folder:

> Read agents/SESSION-HANDOFF.md and agents/PROJECT-BRIEF.md. We're continuing the grilling session (grill-with-docs) about winning the Gemma 4 competition. Pick up from "Open questions" below.

## Who and what

- Group 9, CS/CE 351/363 AI, Fall 2026: Syed Ibad Asim (the user) and Areesha Ashfaq. Team of 2.
- Project: improve a Gemma 4 coding agent for Kaggle "Google - The Gemma 4 Developer Agent Competition" (main track, due Dec 2) and write a paper for its Paper Track (due **Nov 12, 23:59 UTC**).
- Goal: course grade is the floor; aim to win a paper-track prize, with the E4B $10k small-model bonus as a stretch.

## How the user wants to work

- **Only official competition rules, models and data.** No outside benchmarks (no SWE-bench Lite or SWE-rebench). Flag anything external as a question.
- Plain words. When something is unclear, they ask for `/pstack:bro`-style rewrites. Keep answers short.
- Grilling format: numbered questions, each with a recommended answer, worded so "yes" accepts it.
- The user and partner write all report and paper prose themselves. Claude does code, experiments, research, figures and number checks.
- **Git: always push as `vanodew1`, never `Vanodew`** (a different account). This repo's local git config has a credential helper that does this on the home PC. On a new machine, check `gh auth status` and use `vanodew1`.
- Commits so far are authored as vanodew1. Nothing was ever pushed from Vanodew; that one attempt was rejected.

## Grilling: decisions made

Q1–Q23 are answered; see the table in `PROJECT-BRIEF.md` §1. In short:
- **Models:** develop on 12B; try E4B for the bonus.
- **Priorities:** course first; team of 2; both of you on the paper team.
- **Paper:** "where does each Gemma size break as the search-word picker, and which cheap fixes recover it".
- **Data and runtime:** the 129 competition dev tasks only; vLLM with the official QAT checkpoints for real runs.
- **Experiment design:**
  - baselines: random, BM25, rules, and Kaggle's own graph and embedding search
  - sizes: E2B, E4B and 12B (26B optional)
  - fixes: voting, code-name merge, forced JSON, 3-shot
  - memory test: yes
  - "fails" = doesn't beat the rules-only score

## Open questions (ask these next)

- **Q24 Prize target:** aim at Best Paper, and release the search tool as a drop-in competition skill so it also qualifies for Best New Resource? (Recommended: yes.)
- **Q25 Schedule:**
  - Nov 2–3: data, vLLM, rebuild the pilot on the competition tasks
  - Nov 4–6: run everything
  - Nov 7: freeze results
  - Nov 8–10: write
  - Nov 11: submit
  - Nov 12: buffer

  (Recommended: yes.)
- **Q26 Main-track agent:** start from the official sample (about 0.08), add the public tips one at a time and log each score, then add the search tool. (Recommended: yes.)
- **Q27 Week 13 interim:** show the size table on the competition tasks plus the first 1–2 leaderboard scores. (Recommended: yes.)
- Add "Are AI coding tools OK if we write the report ourselves?" to the RA questions? (Recommended: yes. The rubric only says the report is checked for AI-generated text.)
- Work split between the two members: postponed by the user.

## Waiting on the user

1. **Kaggle face/identity verification** (required to join; the partner must verify too).
2. **`kaggle.json` API token** in `~/.kaggle/` (Windows: `C:\Users\<you>\.kaggle\kaggle.json`). Never paste its contents into chat.
3. Then: `pip install kaggle` and `kaggle competitions files gemma-4-developer-agent`.

## Next steps for Claude once the data is unlocked

1. Download **all** the competition data (22.42 GB, user's choice) to `comp-data/` next to this repo, on the drive with space (home PC: `D:\AI Project\comp-data\`). Unzip it, delete the zip, and add it to `.gitignore`.
2. Rebuild the pilot on the 129 tasks (`tasks.jsonl` plus `snapshots/`). Gold files = non-test source files the reference `patch` touches. Freeze the rules first.
3. Set up vLLM in WSL2 with the official checkpoints `google/gemma-4-{e2b,e4b,12b}-it-qat-w4a16-ct` (the 12B needs `--hf-overrides`). Keep every model and cache on the data drive, because the home PC's C: has only about 20 GB free.
4. Run the ladder, fixes, baselines and memory test. Paired bootstrap CIs and McNemar tests against the rules.

## Pilot status (code check only, never paper data)

On the 55 old SWE-bench issues, with Ollama Q4_K_M builds:
- Hit@1: 12B 80, E4B 69, E2B 71, rules 69, BM25 58.
- Hit@3: 12B 93, E4B 85, E2B 80.
- Merging rule words: 12B −7, E4B +2, E2B −2 (noise at n = 55).
- No empty replies from any model. E2B takes 0.4 s per call, E4B 1.1 s.

See README "Model size check". All model replies are cached in `data/`, so `python run.py --gemma gemma4:12b gemma4:e4b gemma4:e2b` reruns **without a GPU**.

## Machine notes

- **Home PC:** RTX 5070 Ti 16 GB. Ollama models at `D:\OllamaModels` (`OLLAMA_MODELS`): gemma4:12b, e4b, e2b. WSL2 Ubuntu and Docker Desktop are installed.
- **Laptop:** clone, then `pip install datasets rank_bm25 "pytest==8.3.5"` and clone `repos/requests` and `repos/flask` (see HANDOFF.md). Heavy GPU runs should stay on the home PC unless the laptop has a GPU.
- Claude's memory files live only on the home PC; the key one (competition-only scope) is copied into this file.
