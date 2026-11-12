# What in the harness moves the score most?

Type: research
Status: resolved

## Question

Which levers in the competition harness (time and tool budgets, scoring mechanics, context limits, graph tools, agent structure, model size, LoRA, local evaluation) most raise resolution rate, and what is still unknown and must be measured?

Findings go to `pilot/agents/sources/harness-winning-levers.md`.

## Answer

Ranked levers, numbers and unknowns are in `pilot/agents/sources/harness-winning-levers.md`. Top of the list: an `eval_config.yaml` that fits 12 hours (starting point about 5 minutes per task), 31B for the main slot, running the whole nearest test file before submitting, `grep -n` then ranged `read_file` for localization, forcing an early edit, and rewriting the sample prompt.

Limits: Kaggle pages could not be read, so Kaggle facts are second-hand via `competition-rules.md`. `swegemma`, `adk-submission` and `adk-eval-core` are not in the dataset, and `pip index` found none of them on PyPI (2026-11-09), so no harness behaviour was run.
