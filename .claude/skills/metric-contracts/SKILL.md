---
name: metric-contracts
description: Symbolically check the code that turns Gemma replies into paper numbers (Hit@k, Recall@k, selector order parsing, named-first rerank) with CrossHair. Use whenever a change touches pilot.py hit_at_k/recall_at_k, experiments.py parse_order/answer_list/named_first, or any code that reorders candidate files before scoring.
---

# Metric contracts

**What is promised:** every number in the results tables counts a file as found only if it really is in the model's top k, and the selector and rerank steps only *reorder* candidates; they never lose or invent a file.
**Harm if broken:** the paper reports gains that the method didn't make, and judges or graders who rerun it get different numbers.

## Run

From `pilot/`, with the venv (CrossHair 0.0.112, installed via `pip install crosshair-tool`):

```sh
PYTHONPATH=. .venv/Scripts/python -m crosshair check --analysis_kind=asserts --per_condition_timeout=20 verification/metric_contracts.py
```

- **No output and exit 0:** no counterexample within CrossHair's search bound.
- **Any `error: AssertionError ... when calling <check>(args)` line:** a counterexample. Read the arguments as the inputs that break the rule.

It takes about 1–2 minutes.

## What each check covers

| Check (verification/metric_contracts.py) | Code it covers | Rule in plain words |
|---|---|---|
| `parse_order_is_a_permutation` | `experiments.py`: `parse_order`, `answer_list` | Whatever the model replies, the result is an ordering of exactly the n candidates |
| `named_first_is_a_permutation` | `experiments.py`: `named_first` | The no-call rerank returns the same files, reordered |
| `hit_at_k_matches_definition` | `pilot/pilot.py`: `hit_at_k` | Hit@k is true exactly when a gold file is in the top k, and never drops as k grows |
| `recall_is_a_fraction` | `pilot.py`: `recall_at_k` | Recall@k is in [0, 1], and equals 1 only when every gold file is in the top k |

**Bounds:** n ≤ 6 candidates, ≤ 6 ranked files, ≤ 3 gold files, ≤ 3 path keywords, and CrossHair's 20 s per condition. A pass is a bounded symbolic search, not a proof for every size.

**Not covered:**
- `rank_files` scoring, `gold_files` diff parsing, `extract_keywords`
- the model replies themselves
- the TLA+ design model of the planned agent pipeline. That's a separate design check; read its results with the `/statechart` skill.

## Proven able to fail (2026-11-02)

- Removing `parse_order`'s fallback (`return picked`) gave the counterexample `parse_order_is_a_permutation('', 1)`.
- Changing `hit_at_k` to slice `ranked[:k + 1]` gave the counterexample `hit_at_k_matches_definition(['', ''], [''], 0)`.

## Real bug vs modeling error

- **Real bug:** a counterexample whose inputs are ones the pipeline can produce, such as an empty or chatty reply, or duplicate gold paths. Fix the product code, not the contract.
- **Modeling error:** the counterexample needs inputs the callers never pass, such as k < 0. Tighten the precondition asserts only then, and say why in the commit message.
- **Intended behavior change** (for example, Hit@k counted on function names): rewrite the matching check, show it failing on a broken variant first, then update the table above.

## Sync record

Last confirmed to describe the code at commit **bbbd842** (`pilot.py`, `experiments.py`, `verification/metric_contracts.py`). If those functions changed after that commit, rerun the check and reread each covered function. Move this commit forward only after you've confirmed the checks still describe the code.
