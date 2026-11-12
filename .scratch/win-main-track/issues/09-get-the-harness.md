# Can we get the harness to run ourselves?

Type: task
Status: resolved
Blocked by: 01

## Question

Where can `swegemma`, `adk-submission` and `adk-eval-core` be obtained? They are not in the dataset and `pip index` found none on PyPI (2026-11-09). The user checks the competition's Code tab and official starter notebook on Kaggle, and whether a notebook attached to the competition can import them. Record what was found and where, since local scoring depends on it.

## Answer

The official starter notebook (pasted by the user, 2026-11-09) installs all three from 41 wheels in the Kaggle dataset `metric/gemma-4-developer-agent-wheelhouse`, then runs `swegemma.evaluate.Evaluator` on dev tasks with `sandbox='subprocess'`, including verification. So the real harness runs inside a Kaggle notebook attached to the competition. Running it at home has not been tried.
