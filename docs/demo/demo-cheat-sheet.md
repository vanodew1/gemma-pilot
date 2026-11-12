# Demo cheat sheet: Group 9, Gemma 4 coding agent

Kaggle: Google - The Gemma 4 Developer Agent Competition. Entry deadline Nov 25, final Dec 2, 2026.

## 1. Problem

- **Task:** given a real Python codebase and a bug report, an AI agent must find the faulty code and write a fix that makes the project's tests pass.
- **Twist:** every team must use the same small Gemma 4 model (4-bit). Teams can't change the model, only the agent built around it: the prompt, the tools, the number of agents and the budgets.
- **Why it matters:** today's strong coding agents run on huge cloud models. This asks whether a small open model running offline on modest hardware can fix real bugs. That means cheaper, private, local developer tools.
- **Our question:** which agent design choices help a small model the most?

## 2. Input / Output

- **Input:** a repo (at `/workspace`) plus the bug report text, which is inserted into our prompt as `{problem_description}`.
- **Output:** a patch (a unified diff from `git diff`), sent with the `submit_patch` tool.
- **What we submit:** `submission.zip` holding the agent config, not code.
  - `agent.yaml`: Google ADK format, naming the model, tools and sampling settings
  - `eval_config.yaml`: the time and action limits per bug
  - `prompts/*.md`: the instructions
- **How Kaggle scores it:**
  1. Runs our agent on about 120 hidden bugs.
  2. Applies each patch and runs that bug's tests.
  3. Counts a bug as resolved if its tests pass; the score is the fraction resolved.
  4. The public board uses 58 of the bugs, so 1 bug is about 0.017.
- **Hard limits:** 12 hours on 4×L4 GPUs for all bugs; going over scores 0. One submission per day.
- **Kaggle provides:** the model, 9 harness tools (`run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`, plus 3 code-graph tools), the sandbox and the grader. We only choose from these; custom Python tools aren't allowed.

## 3. Literature review (3 papers)

| Paper | Core idea | How it handles input and output | How we use it |
|---|---|---|---|
| **SWE-bench** (Jimenez et al., ICLR 2024) | Benchmark of 2,294 real GitHub issues from 12 Python repos. A fix counts only if the issue's tests pass (FAIL_TO_PASS) and the old tests still pass (PASS_TO_PASS). | Repo + issue in, patch out | Defines our exact task and scoring. The competition is SWE-bench style. |
| **SWE-agent** (Yang et al., NeurIPS 2024) | Agent-Computer Interface (ACI): give the LLM simple, LM-friendly commands (search, open a file window of about 100 lines, edit) and rejects edits that have syntax errors via a linter. Design of the tools matters as much as the model. | Repo + issue in, patch out, with tool calls in a loop | v1: grep exact names, read narrow windows, small edits. v6: its gates check the edit compiles (`py_compile`), the same idea as SWE-agent's edit linter. |
| **Reflexion** (Shinn et al., NeurIPS 2023) | Verbal reinforcement: after a failed try, the agent writes a reflection from the feedback (such as test errors), keeps it in memory, and retries. No weight updates. | Task + feedback in, improved answer out | v1: test then repair (step 4–5). v6: a separate checker gets feedback (compile and test result) and repairs. |

**One line:** SWE-bench defines the task, SWE-agent says good tools and navigation matter, and Reflexion says feedback from failure improves the next try. We apply both ideas to a small 4-bit model, where little published work exists.

## 4. Data

- **Source:** the competition's Data tab, official only; no outside data.
- **Dev set:** 129 bugs from 4 repos, each with its reference fix.

| Repo | Bugs |
|---|---|
| fastapi | 67 |
| rich | 48 |
| requests | 13 |
| httpx | 1 |

- **Also released:** code graphs and embeddings. We measured them and they rarely helped, so v1 and v6 leave those tools out.
- **Hidden test set:** about 120 bugs that we never see.
- **Status / key finding:** we built a home bench that runs the dev bugs locally. Even the reference fix passes only 56 of 129:
  - rich: 0 of 48 pass. A test plugin runs `import attrs`, which loads rich's own `examples/attrs.py` instead.
  - requests: 5 of 13 pass, because those tests need the network.
  - Scored over 129, home v1 = 7/129 = 0.054, which matches Kaggle's 0.05. Our bench now predicts Kaggle.
- **Limitation:** only 4 repos, all Python.

## 5. Models explored

- **Model:** Gemma 4 E4B (`gemma-4-e4b-it-qat-w4a16-ct`): instruction-tuned, QAT 4-bit weights and 16-bit activations. Chosen for the $10k small-model bonus.
  - **QAT** = quantization-aware training: the model is trained while simulating the quantization, so the 4-bit model loses little accuracy.
- **Also tested:** Gemma 4 12B at home. It fixed 15/56 vs E4B's 7, but it's slow (median 529 s per bug vs our 4.5 min limit). Not submitted yet.
- **Where we run it:**
  - Kaggle notebook: the script `agent_v1.py` / `agent_v6.py` is pasted into one cell and builds `submission.zip`.
  - Home: `local_bench.py` runs the same agent on the dev bugs and grades it.

**v1: single agent (submission 1)**
- 1 agent, 6 tools, temperature 0.2, thinking budget 2048 tokens.
- Limits: 4.5 min, 40 actions per bug.
- Prompt = 6 steps:
  1. grep exact names from the issue
  2. read only nearby lines
  3. first edit by action 12
  4. run the closest test file
  5. repair if broken
  6. `git diff`, then submit
- Home 7/56. **Kaggle 0.05.**

**v6: pipeline (submission 2)**
- ADK `SequentialAgent` with 4 steps, each starting a fresh context:
  1. **solve**: v1's guide, can't submit, writes a FILE / CHANGE / TEST note
  2. **gate_a**: is there an edit, does it compile, run the test, repair only real breakage
  3. **gate_b**: the same check again with a different seed
  4. **finalize**: only calls `submit_patch`
- Home 10/56. **Kaggle 0.01.** It got worse on Kaggle.
- Likely cause: 4 fresh contexts cost much more time per bug, so solve runs out. Possibly SequentialAgent also behaves differently on Kaggle. Not confirmed; we need Kaggle logs.

| Version | Home (of 56) | Kaggle public |
|---|---|---|
| Official sample agent | — | ~0.08 |
| v1 | 7 | 0.05 |
| v6 | 10 | 0.01 |
| v1 on 12B (10 min) | 15 | not submitted |

## Hard questions, short answers

- **"You're below the sample's 0.08?"** We use the small E4B model for the bonus. 12B doubles our fixes at home (15 vs 7). Submission 1 was a pipeline check.
- **"Why did v6 drop?"** More agents means more time per bug, and our home setup doesn't match Kaggle's speed. Honest negative result; next we test one variable at a time.
- **"Proposal said 31B and a search/retry ablation?"** 31B is too slow for about 120 bugs in 12 hours, and going over scores 0. The ablation is our next step: v1 = search rules, v6 = check and retry.
- **"What's novel?"** Testing published agent ideas (SWE-agent tools, Reflexion feedback) on a tiny 4-bit model, plus the finding that a home bench must reproduce Kaggle's grading (56/129) to predict scores.
- **"Did you train anything?"** No. The model is frozen; all gains come from agent design. LoRA is optional and skipped because GPU time is limited.
