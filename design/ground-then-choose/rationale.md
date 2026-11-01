# Ground-then-Choose localization: runner-1 design

## Problem

One localization method has to serve two callers. The paper harness runs about 12 arms × 3 model sizes over the 129 Kaggle dev tasks and caches every reply. The E4B agent runs inside an offline ADK sandbox, where a script can't call the model: `locate.py` prints, the harness model answers, and the agent acts on the answer. Today the method is split over `pilot.py`, `run.py` and `experiments.py`. Two clients and two caches, keyed by hand (`iid + ":S1"`). Arms exist only as table strings that get parsed back (`m.split(' ')[2]`). `size_label` collides across model families. `metric_contracts.py` imports from `experiments.py`. The hard constraint: the agent has to run *the thing the paper measured*. If S1's prompt and locate.py's output can drift apart, the paper's E4B number says nothing about the submission.

## Usage (caller's view)

Agent (SKILL.md tells the model to do this):

```
$ python skills/fix/scripts/locate.py --issue-file ISSUE.md
[1] httpx/_models.py
class Response
  def raise_for_status
...
[5] httpx/_client.py
...
Order the candidates from most to least likely to contain the code that must change.
Reply with only a JSON list of the candidate numbers, for example [2, 1, 3, 5, 4].
model> [1, 5, 2, 3, 4]
$ python skills/fix/scripts/locate.py --issue-file ISSUE.md --open 1   # windows around hits
... edit with apply.py ...
$ python skills/fix/scripts/finish.py            # diff minus test files, or NO_PATCH
```

Paper:

```
python experiment.py kaggle --models E2B E4B 12B --live   # once, on the GPU box
python experiment.py kaggle --models E2B E4B 12B          # forever after: offline replay, CacheMiss if incomplete
```

In code:

```python
menu = ground.locate(issue, ground.read_tree(repo))          # locate.py and arm S1, the same call
q = ground.choice_question(issue, menu)                      # prompt text + parser
ans = Oracle(cache_dir, live=False).ask(MODELS["E4B"], q)    # experiment only
ranking = menu.order(ans.parsed.value)

@method("S1v", "S1 Borda over 3 menu rotations", model=True)  # a new arm = one function
def S1v(v: View, m: Model) -> Outcome: ...
```

## Shape

Four modules. Calls go at most three files deep: experiment → arms → ground/oracle.

- **`ground.py`** (replaces `pilot.py`; stdlib only; vendored byte-for-byte into `skills/fix/scripts/`). It holds every pure step: keywords, `rank_files`, `read_tree`, `outline`, `windows`, `Menu`/`build_menu`/`locate`, `parse_order`, `named_first`, `resolve_paths`, `borda`, the metrics, and **`Question[A]` = exact prompt + parser**. The load-bearing decision is that a model interaction is data. The module never sends a prompt. It only builds prompts and parses replies. That is why the same code runs where the caller is an HTTP client and where the caller is the ADK harness (per boundary-discipline).
- **`Menu`** is the grounded candidate set. `render()` is its only text form. locate.py prints `render() + CHOICE_INSTRUCTION`, and `choice_question` embeds the same two strings. `pool` is the ceiling. `order(labels)` turns the parsed reply into a Ranking. `tests/test_vendor.py` asserts that the agent's output is a block of the measured prompt.
- **`oracle.py`**: one `Oracle.ask(model, question) -> Answer`. Replies are stored raw in one append-only JSONL per model, keyed by `sha256(tag + prompt)`, and parsed *after* the cache. So a parser fix (like the IDEAS-RUN §6 `parse_order` bug) needs no re-query. A prompt edit can't reuse a stale reply. A crash followed by a rerun converges (per make-operations-idempotent). Each cache file has one writer (per separate-before-serializing). `live=False` turns "reruns need no GPU" into an exception instead of a hope. `Model(label, tag)` is declared once in `MODELS`, which fixes the size_label collision.
- **`arms.py`**: `@method(code, label, model=)` registers the rank function into `METHODS` in definition order. Columns, CSV rows, CLI choices and `COMPARISONS` all derive from it, and comparisons refer to the Method *objects*. So no list is synced by hand, and a deleted arm fails at import. An arm's identity is `(Method, Model | None)`, never a string. `View` memoizes per task, so K2, N, S2 and V share one keyword call, and S1v's rotation 0 and V reuse S1.
- **`experiment.py`**: the corpus boundary (`load_tasks` parses JSONL into `Task` and drops gold-less tasks), `run`, `mcnemar`, CSV and table output, and `--trace`. Both corpora end in a working tree at base_commit, so `ground.read_tree` is the only file reader for the experiment *and* the agent.
- **Skill**: `locate.py` (a thin shell over `ground.locate`), `finish.py` (keeps the TLA+ rule NoTestEditsSubmitted in code, using `ground.is_test_path` so that "not searched" and "not submitted" are one rule), and `apply.py`.

Interface depth: the agent sees one function (`locate`) and one constant. The harness sees `ask` and `@method`. Behind them sit keyword typing, idf ranking, outline rendering, parse fallbacks, cache keying and offline enforcement.

Deliberately not done: graphs/<id>.json is unused (it drops `async def`, and regex outlines over source match what the sandbox can read). `lines_opened`, K0 and "retry clues" are dropped from the default arms, and each comes back as one decorated function. No concurrency.

## Synthesis decision

(Filled by arena.)

## Tradeoffs accepted

- We accept that the vendored copy is a file duplicate in exchange for a sandbox with no import path into the repo. A byte-equality test plus the build step make it derived rather than synced.
- We accept that one prompt asks for a *full order* even though the agent needs only the first number. In exchange, Hit@3 for S arms comes from the same reply, and the agent's prompt is the measured prompt. The agent can answer `[3]`, because `parse_order` fills in the rest.
- We accept that the agent's surrounding context (system prompt, SKILL.md, earlier turns) differs from the experiment's single-turn prompt. Only the menu and instruction bytes are guaranteed identical. Closing the gap fully would need a harness replay, which costs more than it gains now.
- We accept that `@method` binds module names by side effect at import, in exchange for one declaration site. It is mildly magic, but an agent copying the nearest arm gets everything right.
- We accept that the pilot's iid-keyed caches need a one-off re-key (`import_legacy_caches`), and are then deleted. No dual-format reader.

## Alternatives considered

- **Locator object with a pluggable `chooser` callback** (the agent passes a stdin reader, the experiment passes Ollama). It lost because the skill can't block on the model: the model answers in a later harness turn, so a callback interface misstates the control flow. `Question` (prompt + parse) states it correctly: a request and a parser, joined by whoever owns the transport.
- **An arms table as data (YAML/dict of method → params) interpreted by one generic runner**. This hides less: every new arm shape (votes, rotations, probe) grows the interpreter's branches, and arms become strings again. Decorated functions keep each arm's logic next to its declaration.
- **Keeping `run.py` plus `experiments.py` and sharing only a client module.** This is the smallest diff, but it keeps two hit counters and two tables, and leaves arms as strings, which is exactly the code-review finding.

## Implementation reconciliation

(Empty until Phase D.)

## Open questions and risks

- How does locate.py get the issue text in the sandbox? Is it a file the harness writes, or something the agent pastes into `--issue-file`? HARNESS_README.md should settle it before locate.py's CLI is frozen.
- `--open N` recomputes the menu, so it is wrong if run after an edit. Is "locate before any edit" enforceable in SKILL.md, or should locate.py write the menu to a temp file outside the repo?
- Should the paper's headline S1 number use the agent's prompt *with* a SKILL.md preamble, so the measured and shipped contexts match more closely?
- Does `max_model_len=32768` fit KEYWORDS_PROMPT with the full file list on the larger repos (fastapi)? K2 uses `num_ctx 8192` locally today.
- Is the memory probe P still meaningful when the dev repos are public (fastapi, rich, requests, httpx) but the test repos are private? It stays as a reported control, not a claim.

## Next implementation step

Rename pilot.py to ground.py, moving in `parse_order`, `named_first`, `outline`, `windows` and `is_source` with bodies unchanged. Repoint tests/test_pilot.py and metric_contracts.py, and confirm that the CrossHair contracts and the pytest suite still pass before anything new is written.

## Synthesis decision (architect arena, 2026-11-02)

Two structurally distinct candidates:
- **runner 1 (this sketch):** a model call is data; one flat pure `ground.py`; `@method` arms
- **runner 2:** arms as frozen data nodes plus an interpreter in a `ground/` package

Base = runner 1:
- shorter call chains (≤ 3 files)
- the skill sees one function, `ground.locate`
- one vendored file instead of a package, so there's no question about subpackage imports under `run_skill_script`
- parse-after-cache makes parser fixes free

Both runners converged on four things:
- a stdlib-only vendored core
- content-hash cache keys with an offline `CacheMiss`
- arms declared once, with columns and comparisons derived from them
- a test that the agent's printed menu is byte-identical to the block the paper measures

**Graft from runner 2:** an AST import scan in `tests/test_vendor.py` that fails if `ground.py` imports anything outside the stdlib.

**Rejected from runner 2:** an in-house BM25. The skill never runs the BM25 arm, so `rank_bm25` stays in the experiment layer.

**Status:** scaffold only (`NotImplementedError` bodies). Implement after the competition data lands. Migrate `run.py`, `experiments.py` and `pilot.py` callers, then delete them in the same change. `verification/metric_contracts.py` only changes its imports.
