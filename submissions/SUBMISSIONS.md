# Submission log

One entry per Kaggle submission. Each entry records what was sent, why, and what came back.

## Submission 1: agent v1 on small Gemma

- **Status:** submitted 2026-11-11 by direct zip upload; succeeded, public score 0.05
- **Built by:** `agent_v1.py`, pasted into one Kaggle notebook cell. It writes the three files below and zips them as `submission.zip`.
- **Purpose:** prove the entry runs on Kaggle, get our first real score, and measure Kaggle's speed from the run time.

### What is in the zip

| File | Contents |
|---|---|
| `agent.yaml` | One agent named `swe_agent_v1`, the model, its tools and how it writes |
| `eval_config.yaml` | Time and action limits per bug |
| `prompts/system.md` | The guide Gemma reads, with the bug report placed inside it |

No helper agents, skills or trained add-ons (LoRA).

### Settings

| Setting | Value |
|---|---|
| Model | `gemma-4-e4b-it-qat-w4a16-ct` (small Gemma, eligible for the small-model bonus) |
| Tools | `run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch` (6 of Kaggle's 9; the three code-map tools are left out) |
| Temperature, top_p, seed | 0.2, 0.95, 42 |
| Longest reply | 4,096 tokens, of which up to 2,048 for thinking |
| Time per bug | 4.5 minutes (9 hours at most for 120 bugs, under the 12-hour limit) |
| Actions per bug | 40 |
| Longest single command | 120 seconds |
| Turns per bug | 80 |

### The guide, in short

1. Search for exact names from the bug report.
2. Read only the lines around what the search found.
3. Make the first edit by action 12; keep edits small.
4. Run the whole test file closest to the change.
5. If the change broke something, fix it and test again.
6. Check the change with `git diff`, then turn it in.

Rules: change source code only, keep scratch files in `/tmp`, never run `pip`, never run the whole test suite, and turn in work early if warned about the budget.

### Results at home before submitting

Fixed 7 of 26 practice bugs on Ollama and 5 of 26 on llama.cpp, using a downloaded Gemma build that differs slightly from Kaggle's. The `rich` repository stayed sealed. Two rewritten guides (v2, v3) fixed 5 each, so v1 was kept.

### Result on Kaggle

| | |
|---|---|
| Submitted | 2026-11-11, uploaded as `submission.zip` from `bench_runs/submission_preview` |
| Queue wait | none; it showed "Notebook Running" 29 seconds after upload |
| Run time | not shown on the submissions page |
| Public score | 0.05 |
| Errors | none; status "Succeeded" |
| Note | Home practice scored 5/26 (0.19). Kaggle's 0.05 is far lower: harder hidden bugs, the Kaggle Gemma build, or slower Kaggle hardware hitting the 4.5-minute limit. Cause not yet known. Part of the gap is our practice set: it has no `rich` bugs (37% of the 129 dev bugs) and twice the share of easy `requests` bugs (19% vs 10%). Reweighted to the dev mix, home v1 is about 0.09 to 0.13. Time is unlikely to be the cause: no home run of v1 hit the 4.5-minute limit, and the slowest bug took 151 s. |
| Explained | Only 56 of the 129 dev bugs grade at home even with the reference fix (fastapi 50/67, requests 5/13, httpx 1/1, rich 0/48: the sandbox's inline_snapshot plugin runs `import attrs`, which loads rich's `examples/attrs.py` via setup.py's workspace `.pth`, and pytest dies). v1 on those 56 (seed 42, run `20261111-120246`): 7 resolved (fastapi 4, requests 3), all submitted, median 40 s. 7/129 = 0.054, matching Kaggle's 0.05, so the home bench now predicts Kaggle if scored over all 129. Inferred: Kaggle's grader cannot pass the other 73 either. |

## Submission 2: agent v6 on small Gemma

- **Status:** submitted by 2026-11-12; public score 0.01 (user report). Cause not yet known.
- **Built by:** `agent_v6.py`; zip at `bench_runs/submission_v6/submission.zip`
- **Purpose:** check whether the solver-plus-two-checks pipeline runs on Kaggle's real harness, and whether its home gain carries over.

### What is in the zip

Root `agent.yaml` is a SequentialAgent with four steps, each in `sub_agents/`:

| Step | Tools | Job |
|---|---|---|
| `solve` | run_command, read_file, edit_file, write_file, get_status | v1's guide, but cannot submit; ends with a FILE / CHANGE / TEST note |
| `gate_a` | run_command, read_file, edit_file | Fresh context. Checks the edit exists and compiles; repairs only real breakage |
| `gate_b` | same | Same check again, seed 7, sees gate_a's report |
| `finalize` | submit_patch | Submits |

Budgets: 4.5 min, 50 tool calls, 75 s per command, 120 turns.

### Results at home before submitting

On the 56 dev bugs that grade at home (seed 42): v1 7, v6 with the gate bug 9, v6 fixed 10. With the gate bug, 3 seeds: v6 25 vs v1 22. Fixed-v6 seeds 1 and 2 not run (GPU moved to a 12B test).

### Result on Kaggle

| | |
|---|---|
| Submitted | 2026-11-11/12, `bench_runs/submission_v6/submission.zip` |
| Public score | 0.01 (about 1 of 129; submission 1 got 6-7) |
| Errors | none reported |
| Note | Home predicted about 10/129 (0.08). Home gain over v1 was small anyway (3 seeds: 25 vs 22). Pure Kaggle slowness does not fully explain the drop: at the token rate v1 needs to keep 6 fixes (about 11 tok/s), v6 would keep about 4. Suspects: slow Kaggle prefill hurting four fresh contexts, Kaggle's SequentialAgent or `!include` working differently from home, or finalize not submitting. Cause unknown without Kaggle logs. |

## Submission 3 (candidate): agent v1 on 12B

- **Status:** zip built 2026-11-12 at `bench_runs/submission_v1_12b/submission.zip`, waiting for the user
- **What changed from submission 1:** only `model: gemma-4-12b-it-qat-w4a16-ct` (not eligible for the small-model bonus). Same guide and budgets (4.5 min).
- **Why:** at home with a 10-minute limit (run `20261111-231705`), 12B fixed 15 of 56 gradable bugs against E4B's 7, including all 7 of E4B's. But only 6 of the 15 finished within 4.5 minutes at home speed (about 61 tokens/s; median bug 529 s). The Kaggle run shows whether Kaggle's 4 GPUs are fast enough: expect about 0.05 if not, up to about 0.12 if so.
