# Project brief: Group 9, Gemma 4 coding agent

One-file summary of everything decided and researched on 2026-11-02. The detailed, cited notes behind it are in `sources/`:
- `sources/competition-rules.md`: rules, checked against Kaggle's own pages
- `sources/novelty-survey.md`: prior work on localization
- `sources/size-ladder.md`: whether the size-ladder paper is viable, plus datasets and fixes

## 1. Decisions so far

| # | Decision |
|---|---|
| Goal | Course grade is the floor; never trade it away. Updated 2026-11-09: after course work, aim for the highest main leaderboard score, with one final slot on the small-model bonus. Paper track dropped. |
| Model | Develop on Gemma 4 12B. Main-track submissions also tried on E4B for the bonus; if E4B can't beat ~0.10 by about Nov 25, switch all submissions to 12B. |
| Priority | Course deliverables first, except a submission due that day. All other time goes to the main track. |
| Team | Team of 2. Get the RA to confirm this in writing. Both join the paper track as one team before Nov 12. |
| Paper angle | "Where does a small Gemma 4 model break as the search-word picker, and which cheap fixes bring it back?" |
| Data | Python only for now; many repos, a few hundred issues. Lock the method before testing on new data. |
| Writing | Both of you write the prose yourselves. Claude helps with structure, numbers, figures and review. |
| Main track | Starter agent on 12B submitted by about Nov 16, then one submission per improvement. |
| Work split | Postponed. |
| Failing | A model fails if its Hit@1 doesn't beat the rules-only score on the same tasks. |
| Scope | Only the official competition's rules, models and data. Dataset = the 129 dev tasks (4 repos); report the small number of repos as a limitation. |
| Runtime | Real runs use vLLM with the official `-it-qat-w4a16-ct` checkpoints, as Kaggle does. Ollama is only for quick checks. |
| Baselines | Random, BM25, rules-only, plus Kaggle's built-in search (graph tools and embedding search). |
| Sizes | E2B, E4B, 12B. 26B only if there's spare time. |
| Fixes | Voting, code-name rule merge, forced JSON output, 3 worked examples. Test-error retry dropped from the paper; it stays in the agent. |
| Memory test | Yes: ask for the file with no search, for each size. |
| Pilot data | The old 55 SWE-bench issues are only for checking the code, never for the paper. |

## 2. Competition facts (verified)

**Main track** (`gemma-4-developer-agent`):
- Deadline Dec 2; team merge by Nov 25.
- Allowed models: 31B, 12B, E4B or E2B (QAT), the same model for every agent in a submission.
- About 120 hidden Python tasks; the public board uses 58 of them, so one task is about 0.017. Pass/fail on each task's tests. The private board decides prizes, using the better of your 2 final picks.
- Limits: 12 hours on 4×L4 for all tasks. **Going over scores zero.** 1 submission a day, only 1 pending at a time, and queues have reached 14–33 hours.
- Submission: `submission.zip` containing `agent.yaml` (Google ADK), plus optional prompts, sub-agents, skills and LoRA adapters.
- Leaderboard (Nov 2): 4,355 teams. Top score 0.29, median 0.15. The sample agent scores about 0.08.
- **$10k bonus for the best E2B/E4B entry.** The current best small-model score is 0.10.
- Dev data: 129 tasks (fastapi, rich, requests, httpx) with reference fixes, plus code graphs and embeddings (participants say semantic search rarely helps).
- Public tips: a single agent, a hard cap on tool calls, forcing an edit by about the 12th call, and keeping thinking on. One participant measured 31B ≈ 9–11/31, 12B ≈ 4/31 and E4B 0/31 on local tasks.

**Paper track** (`gemma-4-developer-agent-paper`):
- Deadline **Nov 12, 23:59 UTC**, which is also the last day to join.
- At most 3,000 words. Title, abstract, captions and tables count; figures and references don't.
- Judged on five equal criteria: novelty, quality (how general), relevance, verifiability and clarity.
- Prizes: Best Paper $15k, Best New Resource $10k, Best New Application $10k.
- Main-track entry not required. arXiv preprints are fine. Code can stay private until Dec 2.
- Host: "Purely LLM generated 'slop' will not score well."
- Unanswered by the host: whether smaller models are OK in the paper track, and whether one person can be on different teams across the two tracks.

**Course rubric** (20 points):
- Proposal 1
- Interim (Week 13) 3
- Peer evaluation 2
- Final demo 14:
  - problem formulation 2
  - literature review (3 papers) 3
  - results 2
  - **presentation 5**
  - report written as a paper 2 (checked for AI-written text)

## 3. Is the idea new?

**Already done by others:**
- "An LLM picks search words, and that beats BM25": Caumartin & Melo, arXiv:2512.07022. Local Qwen 30B; Hit@1 on SWE-bench Lite went from 0.40 to 0.48.
- "Small models write grep queries": Lasbordes et al., arXiv:2610.05099, with 1–2B models. Untrained, they do badly (File-F1 18.75); training fixes them.
- The function-name bonus (BLUiR, 2013), typed word rules (BLIZZARD, 2018) and searching again with test errors (FaR-Loc, OrcaLoca).

**Not done, as far as the search found:**
- Keep the search scoring frozen, step through model sizes in one family, find where each size breaks, then measure which cheap fixes recover the small ones.
- Any published Gemma 4 localization numbers.

**Verdict:** viable, novel in a narrow but defensible way. Each fix on its own is known; what's new is how each fix interacts with model size.

## 4. Paper plan

**Claim:** on the competition's own dev tasks, find the smallest untrained Gemma 4 model whose single-call search words beat a zero-parameter rule extractor. Explain why the small models miss and which inference-time fixes recover them, with cost measured on a 16 GB consumer GPU.

**Scope rule (user, Nov 2):** use only the official competition's rules, models and datasets. Nothing external.

**Data:**
- The competition's own 129 dev tasks (fastapi, rich, requests, httpx), each with its reference fix. These replace SWE-bench Lite and SWE-rebench.
- Gold files: non-test source files the reference fix touched. Drop tasks with no gold files and report how many.

**Ladder:** E2B, E4B, 12B and 26B-A4B, all QAT. Thinking off, temperature 0. The 26B-A4B doesn't fit fully in 16 GB and spills to CPU; measure its speed on day 1.

**Floors:** random; BM25 on the raw issue; K1 rules (no model); a memory test that asks for the file with no file list and no search.

**Fixes**, one at a time at each size, then the best combination per size:

| Fix | Expectation | How new |
|---|---|---|
| Voting (5 samples, keep the words that come up most) | Probably the strongest for small models | Medium |
| Merging rule words into the model's words (code names only) | Predicted to help E2B and hurt 12B; that would explain the pilot's 80→73 drop | **High** |
| Forcing valid JSON output (Ollama `format`) | Helps only if small models output broken lists | Low (control) |
| 3 worked examples in the prompt | Moderate gain; watch for copied names | Low (control) |
| File-list hint: none, pruned or full | Saves tokens on big repos | Medium |
| Searching again with test errors | Already known, and the pilot gain was tiny | Drop, or report as an upper bound |

**Metrics:**
- Hit@1/3/5.
- Why it misses: broken output, words with zero search hits (made up), words copied from the examples.
- Cost: tokens, seconds and memory.
- Statistics: paired bootstrap CIs and McNemar tests against K1. At n = 300, differences under about 5 points can't be resolved.

**Main figure:** Hit@1 vs model size, one line per fix, with K1 and BM25 as flat lines; Set A and Set B side by side.

**Budget:** about 22 GPU-hours for everything, so 5 days is enough. Biggest engineering risk: cloning about 300 repos for Set B, so start that first.

**Risks:**
- No breaking point: E2B is already fine because the scorer does the work. Then the story becomes "the scorer makes size matter less", with the cost curve as the result.
- Memorization on Set A: make the claims from Set B.
- 26B too slow: run it on Set B only.
- Tuning bias: the pilot's rules were tuned on requests/flask. Freeze them now.

## 5. How it links to the competition

1. **Main track:** the search step is tool (A) in the agent. A cheap, accurate first file saves tool calls and time under the 12-hour limit.
2. **E4B bonus:** the paper's best fix for small models goes straight into the E4B submission.
3. **Paper track:** this is the submission itself.
4. **Course:** the related-work section is the literature review, the floors are the baselines, and the size table is the interim result.

## 6. Pilot status

- 55 issues (requests 44, flask 11).
- `run.py --gemma <models...>` now runs several model sizes and logs empty replies, number of words, seconds and output tokens per call.
- 12B reproduces the earlier numbers: Hit@1 80% vs rules 69% vs BM25 58%.
- Size check on the 55 old issues (code check only, not paper data):
  - Hit@1: 12B 80, E4B 69, E2B 71, rules 69.
  - Hit@3: 12B 93, E4B 85, E2B 80, rules 91.
  - Merging rule words: 12B −7, E4B +2, E2B −2.
  - E2B takes 0.4 s per call, E4B 1.1 s.
  - Takeaway: 12B is clearly ahead; E2B and E4B are at the rules level. The merge crossover isn't clear at this sample size.
- Caveat: these Ollama tags are Q4_K_M, not QAT. Switch to the `-it-qat` tags for the real paper runs.

## 7. Glossary

- **Issue**: the bug report text.
- **Task**: one issue plus the codebase at the buggy version.
- **Resolved**: the patch applies and that task's tests pass.
- **Patch**: the code change the agent produces.
- **Localization**: ranking which files need to change, measured by Hit@k.
- **Hit@k**: share of tasks where a file the real fix touched is in the top k.
- **Search words**: words used to search the code, picked by rules or by Gemma.
- **Attempt**: one write-patch-and-run-tests cycle; at most 3.
- **Retry clues**: text from a failing test run, fed into the next search.
- **Failing (model)**: proposed: Hit@1 not above K1 rules on the same issues.

## 8. Open questions for the RA or the host

1. Is a group of 2 OK?
2. Can the course paper reuse code shared with the Kaggle team?
3. Are smaller models allowed in the paper track?
4. Can one person be on a team in each of the two competitions?
