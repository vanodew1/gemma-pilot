# Decisions

What's been decided, what's still open, and what's next. Competition facts are in `COMPETITION.md`; words are defined in `../GLOSSARY.md`. Old run logs are in `archive/` (read `archive/IDEAS-RUN.md` §9 before trusting anything in it).

Last updated 2026-11-04.

## 1. Decided

| # | Decision |
|---|---|
| Goal | Course grade is the floor; never trade it away. Bets to win: paper-track prize (main), E4B small-model bonus (stretch). Main-track top 3 dropped. |
| Model | Develop on Gemma 4 12B. Main-track submissions also tried on E4B for the bonus; if E4B can't beat ~0.10 by about Nov 25, switch all submissions to 12B. |
| Priority | Course deliverables first, except a submission due that day or the paper deadline. |
| Team | Team of 2. Get the RA to confirm this in writing. Both join the paper track as one team before Nov 12. |
| Paper angle | Small-model file localization on the competition tasks. Which version (A or B) is still open; see section 2. |
| Data | Python only. Lock the method before testing on new data. |
| Writing | Both of you write the prose yourselves. Claude helps with structure, numbers, figures and review. |
| Main track | Starter agent on 12B submitted by about Nov 16, then one submission per improvement. |
| Work split | Postponed. |
| Failing | A model fails if its Hit@1 doesn't beat the rules-only score on the same tasks. |
| Scope | Only the official competition's rules, models and data. Dataset = the 129 dev tasks (4 repos); report the small number of repos as a limitation. |
| Runtime | Real runs use vLLM with the official `-it-qat-w4a16-ct` checkpoints, as Kaggle does. Ollama is only for quick checks. |
| Baselines | Random, BM25, rules-only, plus Kaggle's built-in search (graph tools and embedding search). |
| Sizes | E2B, E4B, 12B. 26B only if there's spare time. |
| Fixes | (Direction B) Voting, code-name rule merge, forced JSON output, 3 worked examples. Test-error retry dropped from the paper; it stays in the agent. |
| Memory test | Yes: ask for the file with no search, for each size. |
| Pilot data | The old 55 SWE-bench issues are only for checking the code, never for the paper. |

## 2. Paper direction (not yet chosen)

Two candidates. Both use only the 129 competition dev tasks and are decided by a cheap check once the data is downloaded.

**A. "Pick, Don't Write"** (recommended by the 2026-11-02 ideas run; still a hypothesis):
- Claim: with retrieval held fixed, small Gemma 4 models find the right file more often by **picking** one of 5 candidates (shown as class/def outlines) than by **writing search words**.
- Pilot signal (55 old issues, code check only): picking beat writing at every size. Only 12B vs rules was significant (+11/−2, p = 0.02). Memorization isn't ruled out: with no file list, E4B and 12B still named the right file 64% of the time.
- Needs the masked-path and memory-probe controls. Full plan: `archive/IDEAS-RUN.md` §8.
- Kill criteria: the rules' top 5 has the right file under 85% of the time; E4B pick − write under +5 points with a CI including 0; the gain shows up only on memorized tasks.
- Fallback paper (Best New Resource): "What the Dev Set Hides", an audit of the official graph and embedding tools plus the memory probe by size.

**B. Size ladder plus fixes** (the original plan): where each Gemma size breaks as the search-word picker, and which cheap fixes (voting, code-name merge, forced JSON, 3 worked examples) recover it. Full plan: `archive/size-ladder.md`.

**First check once data is down:** how often the right file is in the rules' top 5 on the bigger repos (fastapi, rich). It takes minutes and no GPU.

## 3. Is the idea new?

**Already done by others:**
- "An LLM picks search words, and that beats BM25": Caumartin & Melo, arXiv:2512.07022. Local Qwen 30B; Hit@1 on SWE-bench Lite went from 0.40 to 0.48.
- "Small models write grep queries": Lasbordes et al., arXiv:2610.05099, with 1–2B models. Untrained, they do badly (File-F1 18.75); training fixes them.
- The function-name bonus (BLUiR, 2013), typed word rules (BLIZZARD, 2018) and searching again with test errors (FaR-Loc, OrcaLoca).

**Not done, as far as the search found:**
- Keep the search scoring frozen, step through model sizes in one family, find where each size breaks, then measure which cheap fixes recover the small ones.
- Any published Gemma 4 localization numbers.

**Verdict:** viable, novel in a narrow but defensible way. Each fix on its own is known; what's new is how each fix interacts with model size.

## 4. How the work links together

1. **Main track:** the search step is tool (A) in the agent. A cheap, accurate first file saves tool calls and time under the 12-hour limit.
2. **E4B bonus:** the paper's best fix for small models goes straight into the E4B submission.
3. **Paper track:** this is the submission itself.
4. **Course:** the related-work section is the literature review, the floors are the baselines, and the size table is the interim result.

## 5. Open questions

**For you (from the grilling, with recommended answers):**
- Q24 Prize target: aim at Best Paper, and release the search tool as a drop-in competition skill so it also qualifies for Best New Resource? (Recommended: yes.)
- Q25 Schedule to Nov 12: data and vLLM → run everything → freeze results Nov 7 → you write Nov 8–10 → submit Nov 11, with Nov 12 as a buffer. (Recommended: yes; the dates have slipped, so redo them.)
- Q26 Main-track agent: start from the official sample (about 0.08), add the public tips one at a time and log each score, then add the search tool. (Recommended: yes.)
- Q27 Week 13 interim: show the size table on the competition tasks plus the first 1–2 leaderboard scores. (Recommended: yes.)
- Which paper direction, A or B (section 2)?
- Work split between the two of you: postponed.

**Not yet designed** (the professor asked about these): how the agent's search tool works end to end, how testing and retries work inside the Kaggle harness, the edit format, and the tool-call cap. This is the next grilling session.

**For the RA or the host:**
1. Is a group of 2 OK?
2. Can the course paper reuse code shared with the Kaggle team?
3. Are smaller models allowed in the paper track?
4. Can one person be on a team in each of the two competitions?
5. Are AI coding tools OK if we write the report ourselves?

## 6. Blocked on you

1. Kaggle face/identity verification (your partner must verify too).
2. The `kaggle.json` API token in `~/.kaggle/`. Never paste its contents into chat.
3. Then: `pip install kaggle` and download all competition data (about 22 GB) to `comp-data/` next to this repo (home PC: `D:\AI Project\comp-data\`). It's in `.gitignore`.

## 7. Next steps

1. Design the full agent by interview (`/grill-with-docs`), then turn it into a spec and tickets.
2. Once data is down: freeze the rules, rebuild the pilot on the 129 tasks, run the top-5 check, choose direction A or B.
3. Set up vLLM in WSL2 with the official QAT checkpoints.
4. Submit a starter agent on 12B by about Nov 16.
