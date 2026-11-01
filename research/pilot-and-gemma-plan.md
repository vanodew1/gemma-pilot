# Keyword-search pilot and local Gemma plan

Researched 2026-10-30. Professor demo: Monday 2026-11-02.

> **Confirmed 2026-10-30 from Kaggle's own competition metadata (`competitions.CompetitionService/GetCompetition`) [P]:**
> - **Paper track** (`gemma-4-developer-agent-paper`): "Google - The Gemma 4 Developer Agent Paper Track". Deadline **2026-11-12 23:59 UTC**, which is also the last day to join or merge teams. Max team size **5**, so the track is not solo-only. It runs as a hackathon with a single $35k prize, **identity verification required**, up to 5 submissions a day, and 425 teams so far.
> - **Main track** (`gemma-4-developer-agent`): deadline **2026-12-02 23:59 UTC**; join and merge deadline **2026-11-25**. Max team size 5. Submission is `submission.zip`, with a 720-minute GPU limit and 1 submission a day. Prizes total $75k ($37k, $18k and $10k for the top three).
> - Model rules were not in this metadata. They are still **UNVERIFIED** for both tracks.

**How sources are marked.** [P] means a primary source: the official Kaggle page, Google AI docs, a Hugging Face page in the `google/` or `ggml-org/` namespace, Ollama docs, vLLM docs, or PyTorch staff on the PyTorch forum. [S] means a secondary source, such as a third-party guide or a participant's GitHub repo. **UNVERIFIED** means no primary source could be read.

**Limitation.** Kaggle renders its competition pages, including the Rules tabs, with JavaScript. WebFetch and curl got back only the page title. An attempt to read Kaggle's internal API was blocked. So every competition rule below comes from search-engine snippets of the official page or from secondary write-ups. **Open the Rules tab of both competitions yourself before relying on any rule in section 2 or 6.**

---

## 0. Which PDF is which

The two filenames are misleading. Each one holds the other's content.

| File | Actual content |
|---|---|
| `L1_aiProposal (2).pdf` | **Course rubric**: "Project Proposal, CS/CE 351/363 Artificial Intelligence, Fall 2026". Four pages. |
| `Project Proposal (1) (1).pdf` | **Student proposal**: Group 9, "Improving a Gemma 4 coding agent", by Areesha Ashfaq (aa09879) and Syed Ibad Asim (sa09753). Three pages. |

Notes from the rubric:
- Groups are meant to have **three** members. The proposal lists two. Confirm this is approved.
- The project is worth 20 points. The Week 16 final demo is worth 14 of them:
  - problem formulation: 2
  - literature review: 3
  - training, testing and results: 2
  - presentation: 5
  - report written as a research paper, checked for AI-generated text: 2
- Three core criteria must be shown explicitly: **technical rigor, novelty and evaluation**.
- The rubric says the project must "compare it against a simple baseline, evaluate it with the competition's metric".

## 1. The proposal and a keyword-search pilot

### 1.1 What the proposal says

The proposal targets *Google: The Gemma 4 Developer Agent Competition* on Kaggle. It gives an entry deadline of Nov 25, 2026 and a final deadline of Dec 2, 2026.

- **Task:** given a code repository and a bug report (the issue), produce a patch in unified-diff format. A patch counts only if the issue's tests then pass.
- **Required model:** the proposal says `gemma-4-31b-it-qat-w4a16-ct`. Section 2 shows this may be out of date.
- **What is submitted:** an agent configuration. It contains prompts, tools and skills, and optionally LoRA adapters, written as a Google ADK config.
- **Related papers:**
  - SWE-bench (Jimenez et al., 2024): the task and its scoring.
  - SWE-agent (Yang et al., 2024): better code-navigation tools lead to more fixes.
  - Reflexion (Shinn et al., 2023): learning from feedback on a failed attempt and retrying.
- **Agent flow:**
  1. Read the issue.
  2. **(A) Search the repo using keywords from the issue, then open only the matching files and lines.**
  3. Write a patch.
  4. **(B) Run the tests.**
  5. If the tests fail, feed the error back, search again using the new clues, and retry. At most 3 attempts.
- **Experiments:** a 2×2 ablation: Baseline, +Search, +Retry, and Both. Each version runs on the dev set. The proposal also tracks tool calls and time per issue.

**The keyword-finding step (A), as specified.**
- Input: the text of the issue and, on a retry, the text of the test error.
- Process: extract keywords, search the repo for them with grep or ripgrep, and rank the matching files.
- Output: a short list of files with line windows. This is all the model reads.

The proposal does not say *how* keywords are extracted. The pilot is the place to pin that down.

### 1.2 Pilot design (doable by Monday)

**Research question for the demo.** Given only the text of an issue, how often does keyword search put the file(s) that the real fix touched among the top-k files? This is called fault localization.

Measuring this needs no model, no test runs and no Docker. That is why it fits in three days. It is also exactly the input to step 2 of the agent.

**Where the data comes from.** SWE-bench Lite on Hugging Face [P](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite) has 323 instances: a `dev` split of 23 and a `test` split of 300, across 6 repositories in total. Each instance has these fields:
- `repo`, `instance_id`, `base_commit`
- `problem_statement` (the issue text)
- `patch` (the real fix)
- `test_patch`, `FAIL_TO_PASS`

The ground truth is the set of files named in the `patch` diff headers (`diff --git a/<file>`).

**Candidate repos.** Each is small enough to clone and grep in seconds.

| Repo | Why | Where to get issues |
|---|---|---|
| `psf/requests` | Small, pure Python. It is **also one of the four repos in the competition dev set** (fastapi, rich, requests, httpx) per [S](https://github.com/Peoplerepabulic/kaggle-gemma4-developer-agent), so the pilot transfers directly. | SWE-bench Lite `test` split, filtered with `repo == "psf/requests"`. **The instance count is UNVERIFIED** because the HF viewer did not show it. If there are too few, add issues from SWE-bench full. |
| `marshmallow-code/marshmallow` | Small library, and it appears in the SWE-bench Lite `dev` split [P](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite). | Lite `dev` split. |
| `encode/httpx` | A competition dev-set repo [S]. Medium size. | Hand-pick 5 to 10 closed bug issues whose linked PRs touch `httpx/`. Ground truth is the files the PR changed. |

Recommendation: use **requests**, plus marshmallow if you need more issues. Target 10 to 20 issues.

**Pipeline.** One Python script, about 200 lines. It needs `datasets`, `rank_bm25` and ripgrep.

1. **Load:** read the instances and run `git clone` once per repo. For each instance, run `git checkout <base_commit>` (or `git worktree add`) so the search sees the code as it was before the fix.
2. **Extract keywords** from `problem_statement`, using deterministic rules that you can show on screen:
   - Code-shaped tokens:
     - `snake_case`, `CamelCase` and `dotted.paths` (regex `\b[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+\b`)
     - text inside backticks
     - `def`/`class` names
   - Traceback lines: `File "x.py", line N` gives a direct file hit. Exception class names such as `KeyError` and `InvalidURL` also count.
   - Quoted strings, which are often literal error messages.
   - Remaining words: lowercase them, drop English and Python stop-words, and keep identifiers that occur in the repo vocabulary.
   - Weight the categories, for example traceback path 5, code identifier 3, error-message string 3, plain word 1.
3. **Search:** run `rg -n -w --type py <kw>` for each keyword at the base commit. Skip `tests/`, or score it separately.
4. **Rank:** score each file as the sum of (keyword weight × log(1 + hits)). Use a definition match (`def kw`/`class kw`) as a bonus. Output the top-k files. For each file, show ±10-line windows around the strongest hits. That is "open only matching files and lines".
5. **Evaluate:** compute Hit@1, Hit@3 and Hit@5. Hit@k means at least one gold file is in the top k. Also compute Recall@5 over gold files. Report the mean number of lines opened as a context-cost proxy.
6. **Baselines and ablations** (this covers the rubric's "simple baseline"):
   - **B0 random:** k random `.py` files. This is the floor.
   - **B1 BM25 over whole files**, using the raw issue text as the query. This is the sparse retrieval baseline from the SWE-bench paper (Jimenez et al., 2024, section 5). Cite the arXiv paper in the report.
   - **K1 rules-only keyword search** (steps 2 to 4).
   - **K2 K1 with an LLM:** prompt local Gemma 4 with "list the identifiers, file names and error strings to grep for" and merge its output with K1. Optional, and only if Ollama is running (section 4).
   - **Retry stand-in:** for the (B) loop, append the text of the `FAIL_TO_PASS` test names or the assertion text to the query and re-rank. This approximates "search again with the new clues" without running tests.

**What to show the professor.**
1. **One issue end to end:** issue text, then extracted keywords color-coded by category, then the rg hits, then the ranked files, then a check mark if a gold file is in the top 3. A live terminal run or a notebook cell works.
2. **A results table:** Hit@1/3/5 and lines opened for B0, B1, K1 and (K2) over N issues.
3. **A failure analysis:** 2 or 3 misses, and why each one missed. Typical causes are vague issue text, a fix in a file the issue never names, or a common identifier.
4. **How it plugs into the agent:** this function becomes the `search` tool in the ADK agent, and the error text becomes the retry query.

**Mapping to the rubric:**
- Technical rigor: an explicit algorithm plus metrics.
- Evaluation: baselines plus a metric.
- Novelty: the error-text re-query, which links (A) and (B) as the proposal's novelty section already says.
- Clarity of inputs and outputs: issue in, ranked files and line windows out.

### 1.3 Day-by-day to Monday

| Day | Work | Done when |
|---|---|---|
| Fri 10/30 | Install Python 3.11+, `pip install datasets rank_bm25`, and ripgrep (`winget install BurntSushi.ripgrep.MSVC`). Clone requests. Load SWE-bench Lite and list the requests and marshmallow instances. Pick 10 to 20. Derive the gold files from `patch`. | A printed table of instance_id → gold files |
| Sat 10/31 | Write the keyword extractor and the rg search and ranking (K1). Run it on one issue and tune by eye. Add B0 and B1. | One issue traced end to end |
| Sun 11/1 | Batch-run all issues and compute metrics. Write up 2 or 3 failures. Optional: install Ollama and add K2 (section 4) if time allows. | The results table |
| Mon 11/2 | Demo: one trace, the table, the failures, and the next steps. | |

---

## 2. Kaggle competitions

These are **two separate Kaggle competitions**:

| | Main (leaderboard) | Paper track |
|---|---|---|
| Name | Google - The Gemma 4 Developer Agent Competition | Google - The Gemma 4 Developer Agent Paper Track |
| URL | https://www.kaggle.com/competitions/gemma-4-developer-agent [P, title only] | https://www.kaggle.com/competitions/gemma-4-developer-agent-paper [P, title only] |
| Prize | $65k: $37k, $18k, $10k [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/) | $35k: Best Paper $15k, Best New Resource $10k, Best New Application $10k [S](https://internshala.com/competitions/?p=12161), [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/) |
| Total pool | $100k, entry deadline Nov 25, 2026 [S, Kaggle announcement via](https://digg.com/ai/hvmfi8q0) | |
| Deadlines (UTC) | Entry and team-merger deadline **Wed 2026-11-25 23:59**. Final submission **Wed 2026-12-02 23:59** [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/), [S](https://github.com/Peoplerepabulic/kaggle-gemma4-developer-agent). This matches the proposal. | **Thu 2026-11-12 23:59**. This is the paper deadline and also the last day to join or merge teams [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/), [S](https://github.com/usp787/Gemma4_paper_track). Internshala gives "13 Nov 2026, 5:29 AM IST", which is the same instant [S](https://internshala.com/competitions/?p=12161). **That is 13 days from today.** |
| Team size | Up to 5 | Up to 5 [S](https://internshala.com/competitions/?p=12161) |
| Submissions | 1 per day. Up to 2 final submissions [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/) | Up to 5 per day. Up to 2 writeups, and each writeup can win only one award [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/) |

### 2.1 Main (leaderboard) track

- **Model:** the proposal says the 31B QAT model is required. However, a secondary guide says the main track allows **exactly one of four** Gemma 4 QAT variants: 31B, **12B**, E4B or E2B, all `-qat-w4a16-ct`. Every agent and sub-agent must use the same base model, and each agent may carry its own LoRA. The 12B needs an `hf-overrides` vLLM setting, which the starter notebook already includes [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/). Another summary mentions only the 31B [S](https://aiwiki.ai/wiki/gemma_4_developer_agent_competition), seen as a search snippet. **This is a conflict: check the Rules or Overview tab.** If the 12B is allowed, local development and Kaggle submission can use the *same model*. The official 12B QAT checkpoint is listed on Hugging Face [P](https://huggingface.co/google/gemma-4-12B-it-qat-w4a16-ct/tree/main) (10.3 GB, per a search snippet).
- **Submission:** a `submission.zip` with `agent.yaml` at the root. Optional folders are `configs/`, `prompts/`, `sub_agents/`, `adapters/` and `skills/`. Agents are Google ADK Agent Config files and may use only harness tools or `agent_tool` sub-agents. The archive must be 3 GiB or less. LoRA adapters are PEFT `.safetensors` files [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/).
- **Metric:** each hidden task is pass or fail. The score is the percentage of patched repos whose validation tests pass. There are about 120 hidden Python tasks, split between the public and private leaderboards, and the private board decides prizes [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/).
- **Dev data:** 129 public tasks from fastapi, rich, requests and httpx, 22.42 GB in total [S](https://github.com/Peoplerepabulic/kaggle-gemma4-developer-agent). The proposal also mentions a code graph and an embedding dataset. **Their exact contents are UNVERIFIED.**
- **Compute:**
  - Hardware: Kaggle L4x4 (4× L4, 96 GB in total), with internet off. GPU quota is charged at 2×.
  - Time: **12 hours total** for all tasks, including sandbox setup and vLLM start-up but not patch validation.
  - Context: the starter notebook sets `max_model_len = 32768`.
  - Per-task limits such as `max_time_minutes` and `max_tool_calls` go in `eval_config.yaml` [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/).
  - The proposal's "30 h/week" quota figure is **UNVERIFIED**, and at the 2× rate it buys only about 15 hours of L4x4 time.
- **External data and models:** allowed if they are publicly available at no cost or meet the host's "Reasonableness Standard". Open-source code must use an OSI licence that does not restrict commercial use. As of 2026-10-17 there was no ruling on training on Claude- or GPT-generated trajectories [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/).

### 2.2 Paper track

- **Format:** a Kaggle Writeup of **at most 3,000 words**, covering title and subtitle, abstract, introduction, methods and experiments, and related work. An arXiv-ready PDF or a public notebook can be attached through project links. A private Kaggle Resource attached to the writeup is made public after the deadline. The search snippet of the official page says: "Your writeup is the paper… upload an arXiv-ready PDF using the public project link feature" [P snippet](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper).
- **Participation:** the same snippet says "participation in the main competition isn't required to submit to the Paper Track" [P snippet](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper).
- **Judging:** "Submissions are scored on five criteria, weighted equally" [P snippet](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper). Each criterion is scored 0 to 5 and worth 20% [S](https://github.com/usp787/Gemma4_paper_track), [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/):
  - **Novelty:** new insights, or important properties of existing methods.
  - **Quality:** how general the approach is and whether it transfers beyond the competition.
  - **Relevance:** impact on software engineering and agentic learning.
  - **Verifiability:** enough detail on method and data.
  - **Clarity.**
- **Suggested areas** [S](https://github.com/usp787/Gemma4_paper_track):
  - Tuning & Optimization
  - **Code Comprehension**: generating, parsing and embedding code graphs
  - Tasks & Benchmarks
  - Graph Reasoning
  - Novel applications of Gemma 4, DiffusionGemma or code graphs
- **Other rules:** the research must be original and unpublished, though a host reportedly said arXiv preprints are fine. Coding assistants may be used for code, but "purely LLM-generated writing will not score well" [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/).
- **Model flexibility (the RA's claim):** two secondary sources say the paper track rules name no model, so the main track's single-model rule does not carry over [S](https://github.com/usp787/Gemma4_paper_track), [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/). One search summary claimed otherwise but cited nothing. **Verdict: probably true, but UNVERIFIED against the official Rules text.** Also note that "Relevance" and the listed areas name Gemma 4. Running Gemma 4 12B locally fits the spirit of the track even if the rules allow any model.

---

## 3. Gemma 4: what exists

- **Releases** [P](https://ai.google.dev/gemma/docs/releases):
  - 2026-03-31: Gemma 4 in E2B, E4B, 31B and 26B A4B
  - 2026-04-16: MTP draft models
  - **2026-06-03: Gemma 4 12B "Unified"**
  - 2026-10-06: EmbeddingGemma 2
  - That page now says it is deprecated in favour of gemma.ai.
- **Sizes:** five, namely "E2B, E4B, 12B, 31B and 26B A4B" [P](https://ai.google.dev/gemma/docs/core). The 26B A4B is a mixture-of-experts model and the 31B is dense. Context is 128K for the small models and 256K for the medium ones [P](https://ai.google.dev/gemma/docs/core).
- **Your two candidates:** **there is no 8B.** **The 12B exists, so it is the one to use.** The next size down is E4B (about 4B effective parameters).
- **Gemma 4 12B-it** [P](https://huggingface.co/google/gemma-4-12B-it):
  - Size and architecture: 11.95B parameters, dense, 48 layers, sliding window 1024.
  - Context: 256K.
  - Modalities: text, image, audio and video in; text out.
  - Thinking mode: `enable_thinking=True`.
  - Recommended sampling: temperature 1.0, top_p 0.95, top_k 64.
  - Coding scores: LiveCodeBench v6 72.0%, Codeforces Elo 1659. **The card reports no SWE-bench score.**
- **License:** Apache 2.0, linked as the "Gemma 4 license" [P](https://ai.google.dev/gemma/apache_2), [P](https://huggingface.co/google/gemma-4-12B-it). Google also links a Prohibited Use policy whose text was not checked.
- **Memory for the weights alone**, with 20% overhead and *excluding the KV cache* [P](https://ai.google.dev/gemma/docs/core):

| Model | BF16 | 8-bit | 4-bit (Q4_0) |
|---|---|---|---|
| E4B | 17.9 GB | 8.9 GB | 4.5 GB |
| **12B** | **26.7 GB** | **13.4 GB** | **6.7 GB** |
| 26B A4B | 57.7 GB | 28.8 GB | 14.4 GB |
| 31B | 69.9 GB | 34.9 GB | 17.5 GB |

- **Quantized builds:**
  - `ggml-org/gemma-4-12B-it-GGUF` [P](https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF): Q4_0 7.22 GB, Q8_0 12.7 GB, BF16 23.8 GB, plus small MTP draft files.
  - Ollama `gemma4:12b`: 7.7 to 8.0 GB, 256K context [P](https://ollama.com/library/gemma4).
  - Official QAT `google/gemma-4-12B-it-qat-w4a16-ct` [P](https://huggingface.co/google/gemma-4-12B-it-qat-w4a16-ct/tree/main). This is in compressed-tensors format for vLLM, **not** llama.cpp.

**Your GPU, from `nvidia-smi` on 2026-10-30:**
- Card: **NVIDIA GeForce RTX 5070 Ti, 16,303 MiB VRAM**.
- Driver: 610.88, CUDA 13.3.
- At the time, **4.4 GB was already in use** by the desktop plus Valorant, Overwolf, Spotify and others. Close games and overlays before running a model.

**What fits in 16 GB (estimates):**
- **12B at Q4 (about 7.2 GB):** leaves about 6 to 8 GB for the KV cache and runtime. Contexts of 32K or more should fit. Gemma 4's 1024-token sliding window keeps the KV cache small on most layers [P](https://huggingface.co/google/gemma-4-12B-it). **This is the recommended setup.** It also matches the main track's 32K `max_model_len`.
- **12B at Q8 (about 12.7 GB):** fits only with a short context (roughly ≤8K) once the desktop's share is counted. Possible, but tight.
- **BF16 (24 to 27 GB):** does not fit.
- **31B at Q4 (17.5 GB):** does not fit in VRAM. It would need CPU offload and would be slow.

The exact KV-cache size is **UNVERIFIED**. Measure it with `nvidia-smi` while running.

---

## 4. Running it locally on Windows

**Blackwell (sm_120) support:**
- Ollama lists compute capability 12.0, including the RTX 5070 Ti, and needs driver 550 or newer [P](https://docs.ollama.com/gpu). Your driver is 610.
- PyTorch binaries built with CUDA 12.8 or later (2.7.0 onwards) support Blackwell, according to PyTorch staff [P-forum](https://discuss.pytorch.org/t/nvidia-geforce-rtx-5070-ti-with-cuda-capability-sm-120/221509). Install a `cu128`-or-newer wheel. Older cu12x wheels give "sm_120 is not compatible" errors. Some Windows users still hit Triton `ptxas` errors [forum](https://discuss.pytorch.org/t/rtx-5070-ti-blackwell-pytorch-nightly-triton-still-getting-sm-120-is-not-defined-for-option-gpu-name-error/220460), so avoid `torch.compile` on Windows.
- vLLM: "vLLM does not support Windows natively". Use WSL. It needs Python 3.11 to 3.14, and Blackwell needs CUDA 12.8 or later [P](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html).

| Option | Effort | Use it for |
|---|---|---|
| **Ollama** (recommended) | Install from ollama.com, then run `ollama pull gemma4:12b` [P](https://ollama.com/library/gemma4) | Pilot K2, and the main paper-track loop. It has an OpenAI-compatible API at `http://localhost:11434/v1`. |
| llama.cpp | Download a CUDA Windows release, then run `llama serve -hf ggml-org/gemma-4-12B-it-GGUF` [P](https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF) | More control: quant choice, KV-cache quantization, MTP speculative decoding |
| LM Studio | GUI. One-click link from the GGUF page [P](https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF) | Quick manual testing |
| HF transformers | `pip install -U transformers torch accelerate` with a cu128+ torch. `AutoModelForMultimodalLM` [P](https://huggingface.co/google/gemma-4-12B-it) | LoRA training and logit access. BF16 does not fit, so use 4-bit through bitsandbytes or similar (**UNVERIFIED on sm_120 Windows**). |
| vLLM in WSL2 | Ubuntu in WSL, then `pip install vllm`, then serve `google/gemma-4-12B-it-qat-w4a16-ct` | **Same runtime and checkpoint as the Kaggle harness.** Best for checking that local results carry over to the leaderboard. Needs the `hf-overrides` setting from the starter notebook [S]. |

**Calling it from Python (Ollama, OpenAI-compatible):**
```python
from openai import OpenAI
c = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
r = c.chat.completions.create(model="gemma4:12b", temperature=0,
    messages=[{"role":"user","content":"List identifiers, file names and error strings to grep for in this issue:\n"+issue}])
print(r.choices[0].message.content)
```
Use temperature 0 for reproducible ablations, even though the card recommends 1.0 for chat. Write that choice down in the paper.

---

## 5. Paper-track strategy (solo, local Gemma 4 12B)

**Deadline:** 2026-11-12 23:59 UTC, which is **13 days away**. The 3,000-word limit makes this a short paper. Scope it to one clear finding.

**Thesis that grows out of the pilot.** "Cheap, interpretable keyword localization for a small local model: how much do issue-derived keywords and test-failure re-queries recover the files to edit, compared with BM25 and LLM-generated queries?" This fits the "Code Comprehension" and "Tasks & Benchmarks" areas. It scores well on Verifiability (deterministic, reproducible, public code) and on Quality (it transfers to any repo).

**Baselines:** random, BM25 over the issue, and rules-only keywords (K1). The paper's addition is the Gemma 4 12B keyword generator (K2), plus K1 with the error-text re-query.

**Evaluation:**
- Localization: Hit@1/3/5 at file level, and function level if time allows, on SWE-bench Lite (300 test instances [P](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite)). Localization only needs `git checkout`, so the full set is feasible.
- Context cost: lines or tokens opened.
- If time allows, end-to-end resolve rate on a small subset. This needs SWE-bench Docker, which is heavy on Windows; WSL works. Mark it optional.

**Ablations:**
- Keyword categories, leaving one out at a time: traceback, identifier, quoted string, plain word.
- Top-k.
- The weighting scheme.
- Gemma thinking mode on or off.
- Gemma 4 E4B vs 12B as the keyword generator. This is a size ablation, and both are local.

**Statistics:** 95% bootstrap confidence intervals over instances. Report the failure categories.

**Timeline:**

| Dates | Work |
|---|---|
| 10/30 to 11/2 | Pilot plus the professor demo |
| 11/3 to 11/6 | Scale to the full Lite set. Add K2 with Ollama. Run the ablations. |
| 11/7 to 11/9 | Optional small end-to-end subset. Make the figures. |
| 11/10 to 11/11 | Write the 3,000 words yourself. The paper track penalizes purely LLM-generated writing [S], and the course report is checked for AI-generated text (rubric). |
| 11/12 | Submit before 23:59 UTC, which is 04:59 PKT on 11/13 if you are in Pakistan. Times are approximate. |

**Link to the leaderboard work.** The same `search(issue_text, error_text) → ranked files` function becomes tool (A) in the team's ADK agent. The paper's localization numbers justify that design choice in the course report.

---

## 6. Running the two efforts side by side

**Plan:** the main track is a team course project with your partner. The paper track is solo.

**What the rules appear to say:**
1. **They are separate Kaggle competitions** with separate URLs and separate team limits (section 2). The official snippet says participation in the main competition isn't required for the paper track [P snippet]. So being on Team X in the main competition and Team "you alone" in the paper track looks allowed. Kaggle's team rules apply per competition. **This is UNVERIFIED: confirm with the host in the paper track's Discussion forum.**
2. Kaggle's standard rules usually include "one account per participant", "you may not participate in more than one team" within a competition, and "no private sharing outside of teams; sharing is OK if made public to all participants". The rule text could not be fetched here; the wording is known only from other competitions [S](https://www.for9a.com/en/opportunity/kaggle-coding-competition-feedback-prize-evaluating-student-writing). **Check the Rules tab of both competitions.** The open question: if your paper uses code your main-track team wrote privately, is that "private sharing outside a team" across two competitions? **This is an ambiguity. Ask the host or the RA.**
3. External code must be publicly available or reasonable, under an OSI licence [S](https://reconscribe.com/gemma-4-developer-agent-competition-2026/).

**Safe setup:**
- **Publish the shared component**, the keyword-search pilot, as a public GitHub repo under the MIT or Apache-2.0 licence, and/or as a public Kaggle notebook, *before* both efforts use it. Then each effort uses "publicly available code", which settles the private-sharing question. It also earns Verifiability points for the paper.
- **Get your partner's written agreement**, for example in a message, that you will use the shared pilot in a solo paper. List them in the acknowledgements, or as a co-author if they contributed substantially. This matters for **course academic integrity**: the course project is a group deliverable. **Ask the RA whether a solo external paper reusing group work is fine.**
- **Keep the claims separate:**
  - The paper's contribution is the localization study run locally with Gemma 4 12B.
  - The course project's contribution is the full agent with the A×B ablation and its leaderboard score.
  - Each effort cites the other.
- **Order of deadlines:** the paper closes on 11/12, before the main track's team-merge deadline (11/25) and its final deadline (12/2). The paper therefore cannot depend on leaderboard results, and that is fine.
- **One model, if the rules allow it:** if the main track allows `gemma-4-12B-it-qat-w4a16-ct` [S], the team could submit the 12B. Your local results would then match the leaderboard setting directly, and Kaggle GPU quota could be saved for final runs. Trade-off: the 31B is likely stronger on the leaderboard.

**Questions to settle with the RA or host:**
- (a) Is the 12B QAT allowed on the main track?
- (b) Can one person be on a main-track team and a different (solo) paper-track team?
- (c) Can paper-track work reuse code the main-track team keeps private?
- (d) Is a group of two acceptable for the course?
- (e) What is the paper track's model rule, verbatim?

---

## Sources

**Primary:**
- https://www.kaggle.com/competitions/gemma-4-developer-agent (title only)
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper (title and search snippet)
- https://ai.google.dev/gemma/docs/core
- https://ai.google.dev/gemma/docs/releases
- https://ai.google.dev/gemma/apache_2
- https://huggingface.co/google/gemma-4-12B-it
- https://huggingface.co/google/gemma-4-12B-it-qat-w4a16-ct/tree/main
- https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF
- https://ollama.com/library/gemma4
- https://docs.ollama.com/gpu
- https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html
- https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite
- https://discuss.pytorch.org/t/nvidia-geforce-rtx-5070-ti-with-cuda-capability-sm-120/221509

**Secondary (verify):**
- https://reconscribe.com/gemma-4-developer-agent-competition-2026/
- https://github.com/usp787/Gemma4_paper_track
- https://github.com/Peoplerepabulic/kaggle-gemma4-developer-agent
- https://internshala.com/competitions/?p=12161
- https://digg.com/ai/hvmfi8q0
