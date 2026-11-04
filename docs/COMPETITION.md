# Competition and course facts

Everything about the two Kaggle competitions and the course rubric, in one place. Facts only; decisions live in `DECISIONS.md`.

Competition rules were checked against Kaggle's own pages on 2026-11-02. Recheck anything marked [SECONDARY] or [UNVERIFIED] before relying on it.

**Key dates (UTC):**
- Paper track: **2026-11-12 23:59**. Also the last day to join or merge teams.
- Main track: join and merge by **2026-11-25 23:59**; final submission **2026-12-02 23:59**.

**Method.** The Kaggle pages render with JavaScript, but Kaggle's own web backend (`https://www.kaggle.com/api/i/...`, the JSON API the site calls) answers anonymous requests that carry the site's XSRF cookie. The following were pulled verbatim from it:
- the competition metadata (`competitions.CompetitionService/GetCompetition`)
- every Overview, Data, Rules and Evaluation page (`competitions.PageService/ListPages`)
- the full public leaderboard (`competitions.LeaderboardService/GetLeaderboard`)
- forum topics with their comments (`discussions.DiscussionsService/...`)
- rendered public notebooks (`kernels.LegacyKernelsService/GetKernelViewModel` → `renderedOutputUrl`)

The official REST API (`/api/v1`) returns 401 without credentials, and the `kaggle` CLI is not installed.

**Tags.**
- [PRIMARY]: text from a Kaggle competition page, or a post by someone Kaggle marks as HOST or ADMIN.
- [SECONDARY]: a participant's post or notebook.
- [DERIVED]: computed by me from primary data.

Short names for the URLs:
- **M** = https://www.kaggle.com/competitions/gemma-4-developer-agent
- **P** = https://www.kaggle.com/competitions/gemma-4-developer-agent-paper
- **M/d/N** and **P/d/N** = discussion topic N on that competition (`<base>/discussion/N`)

---

## 1. Allowed models; small-model bonus

- **All four QAT variants are allowed:** `gemma-4-31b-it-qat-w4a16-ct`, `gemma-4-12b-it-qat-w4a16-ct`, `gemma-4-e4b-it-qat-w4a16-ct` and `gemma-4-e2b-it-qat-w4a16-ct`. "Every agent and subagent in your submission must use the same model." Different LoRA adapters per agent are allowed. [PRIMARY] M, Overview › "Model Selection, Budget, and Harness Rules". The same list appears in the staff post of 2026-10-11 [PRIMARY] M/d/748287 and in the official Getting Started notebook's `ALLOWED_MODEL_NAMES` [PRIMARY] https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent
  - The 12B needs `--hf-overrides '{"architectures": ["Gemma4ForCausalLM"], "model_type": "gemma4"}'`. Staff say "The scorer has this update already". A weight-loading KeyError was "Fixed in the most recent wheelhouse" (2026-10-12). [PRIMARY] M/d/748287
  - Staff say smaller variants are scored under the same conditions: "everything is the same" (same 4×L4, 12 h, eval_config). Train LoRAs against the unquantized weights at kaggle.com/models/google/gemma-4/transformers. [PRIMARY] M/d/748287
  - Note: HARNESS_README §3.1–3.2 reportedly still says 31B-only. Participants flagged this and staff agreed to update it. [SECONDARY/PRIMARY] M/d/748287, M/d/751104
- **Small-model bonus: $10,000** goes to the highest-ranking submission that uses Gemma **E2B or E4B** as the base model, scored on the private test set. [PRIMARY] M, Overview › Prizes; host post M/d/751104
  - To be eligible, the entry must be one of the team's two final submissions.
  - LoRA is allowed.
  - Eligible entries can also win the main prizes and the Paper Track.
  - The deadline is the same as the main track.
  - The competition API lists the main track's reward as USD 75,000 ($65k + $10k). [PRIMARY] GetCompetition
- Small-model leaderboard notebook (staff), last updated 2026-10-30 23:54 UTC: the top public score is **0.10** (4 teams), followed by many at 0.08. [PRIMARY] https://www.kaggle.com/code/ryanholbrook/gemma-4-developer-agent-small-model-leaderboard

## 2. Metric, tasks, split, limits, submission format

- **Metric:** like SWE-bench, each task is PASS/FAIL. The score is the "percentage of patched repositories that pass the validation tests". [PRIMARY] M, Overview › Evaluation
- **Hidden tasks:** "about 120 tasks in the test set, evenly divided between the public and private splits", curated "from a set of private repositories". [PRIMARY] M, Data. The API returns `leaderboardPercentage: 50`. [PRIMARY]
  - The public split is exactly **58 tasks** [DERIVED]: every score on the board equals floor(k/58, 2 decimals), and no other N from 50 to 69 fits. A participant independently says "14 out of 58" [SECONDARY] M/d/752848, M/d/753524.
  - Staff: "None of the repos in the training tasks are present in the test set… every task in the test set is solvable and validates at 100% with a gold patch." [PRIMARY] M/d/747248
- **Private board:** prizes are decided on it. A team's private score is "the better of the two private leaderboard scores" of its two selected submissions. [PRIMARY] M/d/752220 (host). Whether the final evaluation uses multiple runs is unanswered. M/d/754295
- **Compute and time:**
  - **12 hours** for all tasks, "inclusive of sandbox setup time, but excluding time for patch validation". [PRIMARY] M, Evaluation
  - API values: `maxGpuRuntimeMinutes: 720` and `maxCpuRuntimeMinutes: 720`. [PRIMARY]
  - Hardware: L4x4 (96 GB), internet off. Interactive L4x4 notebooks use quota at 2×. [PRIMARY] M, Overview › Upgraded Accelerators
  - Per-task limits are optional, in `eval_config.yaml` (`timeout_seconds`, `verification_timeout_seconds`, `max_tool_calls`, `max_time_minutes`, `max_turns`). The Getting Started notebook's defaults when the file is absent are 300 s, 300 s, 100 calls, 60 min and none. [PRIMARY] starter notebook
  - Serving: `max_model_len=32768`, TP=4. Compaction in the notebook: interval 15, overlap 2, threshold 14336, retention 5. [PRIMARY] starter notebook
  - Going over 12 h fails the whole submission, with no partial score. [SECONDARY] M/d/752017
  - Scored submissions do not use the personal GPU quota. [SECONDARY] M/d/749224
- **Submissions:**
  - **1 per day**, and up to **2 final submissions**. [PRIMARY] M, Rules §2.2; API `maxDailySubmissions: 1`
  - Since about 2026-10-08, a team may have only **one pending submission** at a time. [PRIMARY] M/d/747519 (admin)
  - Queue waits peaked around 33 h (2026-10-10) and were about 14 h on 2026-10-13. [PRIMARY] M/d/747519
- **Format:**
  - The required file is `submission.zip` (API `requiredSubmissionFilename`). It must have `agent.yaml` at the root.
  - Optional folders: `configs/`, `prompts/`, `sub_agents/`, `adapters/<name>/{adapter_config.json, adapter_model.safetensors}` and `skills/<name>/{SKILL.md, scripts/, resources/}`. [PRIMARY] M, Evaluation
  - The config language is Google ADK Agent Config, with restrictions. `!include` is allowed, but paths may not leave the submission root. Only harness tools or `agent_tool` sub-agents may be used. [PRIMARY] M, Model Selection page
  - Harness tools: `run_command`, `submit_patch`, `get_status`, `read_file`, `edit_file`, `write_file`, `get_code_neighbors`, `search_similar_code`, `get_code_subgraph`. Skills add `run_skill_script` and `load_skill_resource`. [PRIMARY]
  - The archive may be at most 3 GiB, uncompressed, and only certain file extensions are allowed. [PRIMARY] starter notebook asserts. Participant validators list .yaml/.yml/.md/.txt/.py/.json/.safetensors [SECONDARY].
  - Scoring writes `submission.parquet` with columns `id` and `prediction` (a diff, or `NO_PATCH`). [PRIMARY] M, Data
  - Submissions go through a notebook that outputs `submission.zip` (staff: "Your notebook needs to generate a submission file (`submission.zip`)"). [PRIMARY] M/d/743683

## 3. Main-track public leaderboard (pulled 2026-11-02)

[PRIMARY] GetLeaderboard and GetCompetition. Score distribution [DERIVED] from those.

| | Value |
|---|---|
| Teams | **4,355**, with 4,882 competitors and 30,038 submissions; 13,976 users joined |
| Top score | **0.29** (one team, "Yurnero"; 17/58) |
| 2nd–9th | 0.24 (14/58), 8 teams |
| 0.22 / 0.20 / 0.18 / 0.17 | 60 / 261 / 654 / 779 teams |
| **Median** | **0.15** (9/58) |
| Teams at 0.00 | 162 |

- **Official baseline score: not published by the host.** [UNVERIFIED]
  - One participant's log shows the "clean analyzer + coder baseline" (the shape of the sample submission) at **0.08**, and an unmodified fork of the public "LB TOP 1" analyzer+coder bundle at 0.13. [SECONDARY] https://www.kaggle.com/code/hitarthjain0/gemma-4-agent-what-took-lb-0-12-0-24
  - That "LB TOP 1" notebook itself shows 0.12. [SECONDARY] https://www.kaggle.com/code/romanrozen/gemma-eda-baseline-for-a-start-lb-top-1
  - A team named "sample_submission.zip" is at 0.17, but that is not an official entry.
- Same-config noise: one estimate is about ±2–3 tasks on 58. Repeat pairs of one config scored exactly the same. [SECONDARY] M/d/753524

## 4. Paper Track

- **Criteria:** five, weighted equally, each scored 0–5. The final score is their average. [PRIMARY] P, Evaluation
  - **Novelty:** new insights, a deeper understanding, or important properties of existing methods.
  - **Quality:** how general the approach is beyond the competition, and whether it transfers.
  - **Relevance:** impact on software engineering and agentic learning.
  - **Verifiability:** enough detail on how it works, and on how data was obtained and analyzed.
  - **Clarity.**
  - The rubric score is not shared with entrants. Ties go to the paper entered first. [PRIMARY] P, Evaluation. The host says top papers get multiple judges, and a tie would "likely" be broken by original submission time. [PRIMARY] P/d/750338
- **Prizes: $35,000.** Overall Best Paper $15k, Best New Resource $10k, Best New Application $10k. [PRIMARY] P, Rules §1.5
  - Every writeup is considered for all three awards but can win only one. The same five criteria apply "in the context of that prize". [PRIMARY] P/d/743255, P/d/750338
  - Winners are highlighted at a Google-hosted event such as a NeurIPS expo workshop. That event is non-archival. [PRIMARY] P, Description; P/d/743310
- **Length: at most 3,000 words** of "original, unpublished research". Non-archival. [PRIMARY] P, Submission Requirements
  - Host clarifications (2026-10-27): title, abstract, captions and tables **count**. Figures and references do **not** count. An appendix counts as supplementary material that judges may not read. There is no official word counter. [PRIMARY] P/d/743255, P/d/749546
  - If a PDF is submitted through the Public Project Link, "we will just be judging the PDF". The Writeup body is then not judged and not counted. [PRIMARY] P/d/743255
  - Required sections: title and subtitle, abstract, introduction, methods and experiments, related work and citations. A public notebook is optional. [PRIMARY]
  - arXiv preprints are "totally fine", and an arXiv link can be the submission. [PRIMARY] P/d/745872
  - Code is not required; it can be kept private until the main track ends. [PRIMARY] P/d/752667
  - GitHub is acceptable for sharing code. [PRIMARY] P/d/751804
  - Derived labels, regenerated graphs and agent traces may be published if upstream licences are cited. [PRIMARY] P/d/749803, P/d/743255
  - A dataset may be released after the main track ends, with a sample released now for judging. [PRIMARY] P/d/751413
- **Main-track participation is not required.** "Participation in the main competition isn't required to submit to the Paper Track." [PRIMARY] P, Description; host P/d/743012
- **Models:** the Paper Track Rules and Evaluation pages **name no required model**. [PRIMARY] P, Rules and Evaluation (full text checked)
  - The listed topics mention Gemma 4, DiffusionGemma and code graphs. [PRIMARY] P/d/743012
  - The direct question "Can I use smaller model?" (E2B/E4B) has **no host answer**. [UNVERIFIED] P/d/749202
  - External data and models follow the same Rules §2.6 "Reasonableness" standard as the main track. [PRIMARY]
- **AI-written text:** "Use of coding assistants to generate code is absolutely acceptable… I would caution against relying solely on LLMs for the written part. Purely LLM generated 'slop' will not score well. However, if tastefully used, LLMs can improve the writing quality and clarity." [PRIMARY] host, P/d/745712
- **Teams and submissions:**
  - Maximum team size 5. Up to 5 submissions per day and up to 2 final writeups. [PRIMARY] P, Rules §2.1–2.2
  - The host says a team can submit at most two writeups. [PRIMARY] P/d/743255. However, the form currently blocks a second one ("unsubmit your previous writeup"), and this is unresolved. [SECONDARY] P/d/753195
  - Deadline: 2026-11-12 23:59 UTC, which is also the team-merger and entry deadline. [PRIMARY] API, Timeline
  - The API returns `requiresIdentityVerification: true` and `hackathon: true`. [PRIMARY]
- **Same person on different teams across the two competitions:** **no explicit host statement.** [UNVERIFIED]
  - The general rules, which are identical in both competitions, say "you may join or form only one Team". [PRIMARY] foundational-rules §5.b. Each competition has its own rules and its own team limits; the Paper Track is a separate competition (id 163111 vs 149921).
  - "No private sharing outside of Teams… This prohibition includes sharing Competition Code between separate Teams." [PRIMARY] §5.d and §3.x
  - No thread on cross-competition team membership was found.

## 5. Dev set and released graph/embedding data

[PRIMARY] M, Data page, unless marked otherwise.

- **`tasks.jsonl`:** 129 public tasks from fastapi, rich, requests and httpx. Each **includes the reference fix (`patch`) and `test_patch`**, plus `problem_statement`, `hints_text`, `base_commit` and `created_at`.
- **`snapshots/`:** 129 `.tgz` repos at `base_commit`, with forward history removed.
- **`graphs/`:** NetworkX JSON AST call and dependency graphs. There are 256 files: 129 named by task, hard-linked to 127 named by commit. Nodes have `id`, `name` and `text` (source code); edges have `source`, `target`, `type` (e.g. `calls`) and `key`.
  - Host note: `async def` functions are missing from the graphs. Private tasks touch none, so the private graphs will not be updated. [PRIMARY] M/d/745998
- **`embeddings/`:** 256 `.npz` files, holding one 256-dim float32 vector per graph node. They back `search_similar_code`.
  - How the embeddings are generated is not documented on the page. Participants report that semantic search often returns nothing. [SECONDARY] M/d/746250
- **Also provided:**
  - `wheels/`: 124 offline wheels
  - `docker/`: Dockerfile.sandbox and Dockerfile.public (Python 3.13)
  - `sandbox/setup.py`
  - `sample_submission/`: an ADK multi-agent example with dummy 31B LoRAs
  - `HARNESS_README.md`: about 55.7k characters [SECONDARY]
- The hidden test set uses "identical graph generation methods". [PRIMARY]
- Local-environment caveat: in a plain notebook only 52/129 gold patches pass, but 127/129 pass in a scorer-like sandbox. The cause is missing test dependencies such as `typing_inspection` and `dirty_equals`. [SECONDARY] M/d/751487, M/d/747248
- Total download size: about 22.42 GB [SECONDARY, not checked].

## 6. Public notebooks and discussion tips

All [SECONDARY] unless marked. Scores are as the authors state them.

- **Starter:** the official Getting Started notebook (2,157 votes) shows the harness, graph tools, vLLM config and packaging. [PRIMARY] https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent
- **"What took LB 0.12 → 0.24"** (hitarthjain0, updated 2026-10-09) says the stronger bundles share:
  - a single agent
  - graph tools not registered
  - a hard tool-call cap, e.g. `eval_config` of 8 min / 28 calls / 240 s / 80 turns
  - a prompt that forces an edit by about call 12
  - exact names and messages copied from the issue
  - scratch files kept in /tmp and tests never edited
  - `git diff` checked before `submit_patch`
  - submitting once an edit exists

  Worst-case timing: 120 tasks × (cap + ~0.5 min) must fit in 12 h, so a cap of about 5 min or less is safe. https://www.kaggle.com/code/hitarthjain0/gemma-4-agent-what-took-lb-0-12-0-24
- **Ablations on 129 local tasks** (Ayush Thakur):
  - Keep thinking on, with `include_thoughts: true`. Disabling thinking: 48 → 23 solved. Hiding summaries: −16.
  - Temperature, top-p and thinking budget changed results by ≤3 tasks, which is noise.
  - Cutting tool calls from 50 to 25 cost 14 tasks.
  - An analyzer sub-agent gained 1 task.
  - Graph and semantic search showed no gain.

  M/d/746250
- **Model size** (Dmitrii Gluzdov, 31 local tasks): 31B solved 9–11, 12B solved about 4, E4B solved 0. The 12B was not faster per task, and its 8-minute submission timed out. M/d/750974
- **Stronger teacher models** through the same harness solve only +4–5 of 124 tasks more than Gemma 31B. 48 tasks are solved by no model. The authors conclude the ceiling comes from the harness and setup. M/d/747168
- **LoRA:** some claim the top of the board needs LoRAs (M/d/748051). Others report SFT LoRAs that do not beat the base model (M/d/750713, M/d/751596). Mixed evidence.
- **Distillation from external LLMs:** admin, 2026-09-29: allowed "as long as you are using those models in accordance with their model license terms" and the output does not conflict with the competition's licence rules. [PRIMARY] M/d/742807
- **Scorer test conventions:** `-p no:anyio`, pytest.ini overwrite, and every `.py` in `test_patch` run as a target. Don't rely on the repo's pytest config or async plugins. M/d/751707
- **Data leak in local runs:** on public rich tasks the `rich-15.0.0` wheel holds the upstream fixes. Drop trajectories that read outside `/workspace`. M/d/747248

## 7. Course rubric (CS/CE 351/363 AI, Fall 2026)

Source: `docs/course-rubric.pdf`. Our proposal is `docs/project-proposal.pdf` (Group 9: Areesha Ashfaq, Syed Ibad Asim). Note: the two PDFs were originally downloaded with each other's file names; the names here are correct.

The project is worth 20 points:
- Proposal: 1
- Interim (Week 13): 3
- Peer evaluation: 2
- Final demo (Week 16): 14
  - problem formulation: 2
  - literature review (3 papers): 3
  - training, testing and results: 2
  - **presentation: 5**
  - report written as a research paper, checked for AI-generated text: 2

Other rubric requirements:
- Groups are meant to have **three** members. We are two, so get the RA to confirm this.
- Show **technical rigor, novelty and evaluation** explicitly.
- "Compare it against a simple baseline, evaluate it with the competition's metric."
- The proposal's line that only 31B is allowed is wrong (see section 1).

## 8. Running Gemma locally

**Home PC:** RTX 5070 Ti, 16 GB VRAM. Ollama models at `D:\OllamaModels` (gemma4:12b, e4b, e2b). WSL2 Ubuntu and Docker Desktop are installed. Close games and overlays first: on 2026-10-30 they already used 4.4 GB of VRAM.

**Weights-only memory** (20% overhead, no KV cache), from ai.google.dev/gemma/docs/core [PRIMARY]:

| Model | BF16 | 8-bit | 4-bit |
|---|---|---|---|
| E4B | 17.9 GB | 8.9 GB | 4.5 GB |
| 12B | 26.7 GB | 13.4 GB | 6.7 GB |
| 26B A4B | 57.7 GB | 28.8 GB | 14.4 GB |
| 31B | 69.9 GB | 34.9 GB | 17.5 GB |

So 12B at 4-bit fits in 16 GB with a 32K context; 31B doesn't.

**Runtimes:**
- **vLLM in WSL2** with `google/gemma-4-{e2b,e4b,12b}-it-qat-w4a16-ct`: the same runtime and checkpoints as Kaggle. Use it for every number that goes in the paper. The 12B needs `--hf-overrides` (section 1). vLLM doesn't run on Windows natively, and Blackwell needs CUDA 12.8 or later.
- **Ollama** (`gemma4:12b`, Q4_K_M, not QAT): quick checks only. Run one model per process and `ollama stop` between models; `--mode all` in the partner demo can crash with `std::bad_alloc`.
- PyTorch on this GPU needs a cu128-or-newer wheel. Avoid `torch.compile` on Windows.
- Keep models and caches on `D:`; `C:` has only about 20 GB free.
