# Harness levers: how a Gemma 4 agent can score higher

Checked 2026-11-09. Facts and inferences only. Main track deadline: 2026-12-02 23:59 UTC.

**Short names.**
- **README** = `D:\AI Project\gemma-4-developer-agent\HARNESS_README.md` (`L` = line number).
- **Sample** = `...\sample_submission\` (file named each time).
- **tasks.jsonl (computed)** = my own read-only count over `tasks.jsonl`, the snapshots (read in memory, never extracted), `graphs\` and `embeddings\`, run with `python -I`.
- **CR** = `D:\AI Project\pilot\agents\sources\competition-rules.md` (prior notes, secondary). **PB** = `..\PROJECT-BRIEF.md`.
- **(inferred)** = my reasoning, not stated anywhere.

**What could not be checked.**
- The Kaggle pages could not be read: on 2026-11-09 a fetch of `kaggle.com/competitions/gemma-4-developer-agent/overview` returned only the page title (JavaScript shell, login not attempted). So every Kaggle fact below comes through CR, and is only as good as CR. I did not re-pull it through Kaggle's internal API.
- `swegemma`, `adk-submission`, `adk-eval-core`, `scripts/inference.py`, `scripts/metric.py` and the ADK source are **not in the dataset** (no such wheel in `wheels\`, no file by those names under `D:\AI Project`). Everything about their behaviour comes from the README, and none of it could be executed.

---

## Top levers, ranked by expected score gain

| # | Lever | Confidence | Source |
|---|---|---|---|
| 1 | **Ship an `eval_config.yaml` that fits 12 h.** The default is 60 min per task, so about 120 h if serial. Sample values (1 min, 10 calls) are the other extreme. Start at about 5 min per task. A miss may score zero. | High that defaults are unsafe; medium on the exact number | README L554, L559; Sample `eval_config.yaml`; CR L48, L53, L159 |
| 2 | **Use 31B for the main track; use the second final pick for E4B/E2B.** Public local numbers favour 31B strongly. The brief's 12B plan conflicts with that. | Medium (secondary data, 31 tasks) | CR L28–32, L168; PB L13 |
| 3 | **Make the agent test the whole nearest test file before submitting.** The scorer needs zero failures and zero errors in every target file, so a single `-k` test is not enough. | High on mechanism; medium on gain | README L619–627; computed: 97/129 tasks touch an existing test file |
| 4 | **Teach localization by `grep -n` then `read_file` with line ranges.** 183 of 229 existing gold files are over the 150-line read cap (median 568 lines). The issue names the gold file in only 33/129 tasks. | High on the numbers; medium on gain | README L444; tasks.jsonl (computed) |
| 5 | **Force an early edit and keep the working tree in its best state.** Unsubmitted edits are still scored, so an edit left on disk beats a late perfect plan. | High on mechanism; medium on gain | README L593–594; CR L149–157 |
| 6 | **Rewrite the sample prompt and drop graph-first search.** It tells the model to search by keywords with a tool built for symbol names, and carries FastAPI-only advice that won't transfer. | High | Sample `prompts/system.md` L11, L16; README L506 |
| 7 | **Keep thinking on and edits small.** Keep `include_thoughts: true` and the README's 4096 / 16384 pair. Instruct small `edit_file` calls. | Medium (secondary ablations) | README L150, L684; CR L161 |
| 8 | **Use graph tools only for "who calls this?" after localizing.** Gold symbols are mostly present, but 61% of nodes are tests and classes are stubs. | Medium | tasks.jsonl (computed); CR L133, L165 |
| 9 | **Try a skill script for deterministic work** (symbol index, compact test output). Could be strong, but nothing about it can be tested without the harness. | Low; needs a real run | README L144, L353; CR L63 |
| 10 | **LoRA only after 1–8 are done.** Reports are mixed and the QAT question is open. | Low | README L204–214; CR L30, L170 |

Expected gains cannot be stated in tasks: the harness isn't available locally yet, and public-board steps of 1/58 are near the noise (one estimate of ±2–3 tasks, CR L85).

---

## 1. Time budget

**What the harness applies by default.** `max_time_minutes` defaults to 60. `max_tool_calls` defaults to 100 in `inference.py` (none in the CLI). `max_turns` defaults to 500. Command timeout is 300 s (README L554–559; CR L51 agrees apart from turns, see §11). Container setup is excluded from this per-task clock (README L566).

**12-hour limit.** 12 h for all tasks, "inclusive of sandbox setup time, but excluding time for patch validation" (CR L48). So the per-task clock (no setup) and the 12 h clock (with setup) measure different things. `max_time_minutes × tasks` understates the true cost.

**Concurrent or serial?** Neither the README nor the sample says.
- The only concurrency setting is `swegemma eval --concurrency` (README L656). That is the local CLI, not scoring.
- There is no concurrency row in the scorer's env-var table (README L552–563).
- Weak evidence for serial: a participant's 8-minute 12B submission timed out (CR L168), and 8 × 120 = 960 min is over 720 (inferred).

Treat it as **serial** until shown otherwise.

**Tasks not reached.** Not stated in the README. CR L53 says going over 12 h fails the whole submission with no partial score, marked [SECONDARY] from M/d/752017. PB L36 repeats this as fact. Not verified. Plan as if it's true.

**Safe values (inferred).** Worst case, every task hits the cap: 120 × (cap + O) + S ≤ 720 min, with S = vLLM start-up and O = setup plus overshoot per task. Both are unmeasured. With S = 15–30 min and O = 0.5–1 min, cap ≤ 4.75–5.4 min. Starting point:

```yaml
evaluation:
  timeout_seconds: 120     # one test run can't eat the task
  max_tool_calls: 40       # time is the real limit; see below
  max_time_minutes: 5
  max_turns: 80
```

- Do not cut tool calls too hard: one local ablation lost 14 tasks going from 50 to 25 calls (CR L163, secondary).
- A public bundle used 8 min / 28 calls / 240 s / 80 turns (CR L152), but the same note says about 5 min is the safe cap (CR L159).
- `timeout_seconds` is capped by the time left anyway (README L389). A timed-out command does not end the session (README L329).
- Whether an in-flight model call can overrun the time budget is not documented. Keep margin.
- `get_status` is free and shows time remaining (README L417–431). The prompt should use it.
- The sample's `timeout_seconds: 60` would cut off many test runs (Sample `eval_config.yaml` L4).

## 2. Sample submission

**Declares** (Sample `agent.yaml`, `sub_agents/code_analyzer.yaml`, `configs/sampling.yaml`, `eval_config.yaml`):
- Root `swe_baseline_agent`, model `gemma-4-31b-it-qat-w4a16-ct`, adapter `main_lora`.
- Tools: `run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`, the 3 graph tools, and an `agent_tool` to `code_analyzer_agent` with `skip_summarization: true`.
- Sub-agent `code_analyzer_agent`: same model, adapter `tool_lora`, tools `read_file` and the 3 graph tools. **No `run_command`, so it cannot grep.**
- Sampling for both: `temperature 0.2`, `top_p 0.95`, `max_output_tokens 16384`, `thinking_budget 4096`, `include_thoughts true`.
- Budgets: 60 s command timeout, 10 tool calls, 1 minute, 50 turns.
- Adapters: `main_lora` and `tool_lora` are byte-identical (same SHA-256). Rank 4, only layer 0, `q_proj` and `o_proj`, every `lora_B` tensor all zeros. They do nothing (computed; matches CR L137 "dummy").

**Weak as a starting point because:**
- The budgets are too small to work with (10 calls, 1 min). A participant's clean version of this shape scored 0.08 (CR L82, secondary).
- The prompt says "use `search_similar_code` with keywords from the error message … rather than running `find` or `grep`" (Sample `prompts/system.md` L11). The tool is designed for symbol names; keywords only reach a lexical fallback (README L506).
- FastAPI-specific line: "edit executable code under `docs_src/`" (L16). Hidden repos are private and different.
- It targets "under 8–10 turns" (L4) and tells the model to run one test or method (L19). That misses the whole-file rule (§3).
- It says modifying tests is "an automatic evaluation failure" (L32). The README says they are stripped (README L615).
- Adapter weights are dead weight, and the analyzer adds model calls inside a tight time budget.
- Public evidence: an analyzer gained 1 task in one ablation (CR L164, secondary).

## 3. Scoring mechanics

- **Protected files are stripped.** Test files (`test_*.py`, `*_test.py`, `.py` under `tests/`, `test/`, `testing/`) and config (`conftest.py`, `pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`, `.pytest.ini`, `sitecustomize.py`, `usercustomize.py`, `_swegemma_stubs.py`, `*.pth`) (README L591, L607). Nothing can be gained by editing them.
- **`pyproject.toml` fixes.** **0 of 129 gold patches touch a protected path** (278 gold file entries, all `.py`) (computed, using README L591 by basename and path). So on the dev set this never costs anything. Unknown for hidden tasks. Note all 278 are `.py`: no docs or config at all. Either the tasks were selected that way or non-code changes were filtered out. If a real fix needs a dependency change, it can't be made and would be lost (inferred).
- **Source files that match test names are lost too** (inferred). A real module named `test_helpers.py`, or a package at `src/x/testing/`, would have its edits silently stripped. 0 dev cases, unknown for private repos.
- **Fallback.** No `submit_patch` needed for scoring: at timeout or budget end the harness still diffs the tree and strips protected files (README L593–594). So never leave half-finished edits; if an experiment fails, restore with `git checkout -- file` (inferred).
- **Empty patch** cannot pass. The sample prompt's check of `patch_size` comes after `submit_patch`, when the session is about to end. Check `git diff --stat` before submitting (README L356, L692; inferred).
- **4-pass apply** (README L601–605). The patch comes from the same tree, so apply failure should be rare (inferred). Nothing to gain.
- **Scratch files in `/workspace` get into the patch** (README L688). Not fatal on its own (test-named ones are stripped), but `workspace_paths.pth` puts `/workspace` and its top-level folders on `sys.path` (`sandbox\setup.py` L307–315), so a file like `/workspace/utils.py` could shadow a real module (inferred). Keep all scratch in `/tmp`.
- **JUnit rules.** Exit code 0 and `passed_tests > 0`, `failures == 0`, `errors == 0`, and every required test passed and not skipped (README L625–627). `tasks.jsonl` has no `FAIL_TO_PASS` or `PASS_TO_PASS` field. Targets are the test files in `test_patch` (README L619; CR L172). So one broken test in that file fails the task.
- **Never `git commit`.** `submit_patch` diffs against `_swegemma_baseline` or falls back to `HEAD` (README L407, L588). The README never says how that ref is made. If it does not exist, a commit by the agent would empty the patch (inferred).
- **Fixed verification timeout** 300 s (README L560). A patch that makes tests hang fails.

## 4. Dev-set statistics (`tasks.jsonl`, computed)

| Statistic | Value |
|---|---|
| Tasks per repo | fastapi 67, rich 48, requests 13, httpx 1 |
| Files per gold patch | median 1, mean 2.16, p90 4, max 26 |
| One file | 91/129 (70.5%) |
| One file and one hunk | 58/129 (45.0%) |
| Lines changed | median 12, p25 4, p75 44, p90 128, max 12,714 |
| Change size buckets | 1–5: 43, 6–15: 30, 16–50: 27, 51–200: 19, >200: 10 |
| One file and ≤15 lines / ≤30 lines | 68 (52.7%) / 80 (62.0%) |
| >200 lines or ≥5 files | 13 (10.1%) |
| Non-empty `hints_text` | **0/129** |
| Problem statement chars | median 418, p25 146, p75 1,000, p90 1,891, max 10,095 |
| Under 100 / 200 chars | 24 / 38 |
| Statement is a PR template (`## Pull Request`) | 7 |
| New gold file | 11 tasks |
| Issue names the gold file or stem / gold symbol | 33 (25.6%) / 36 (27.9%) |
| Existing test file in `test_patch` | 97/129 tasks |
| Test files in `test_patch` | 222 existing, 60 new |

**What follows for an agent.**
- About half the tasks are small one-file fixes. Those are the score.
- Issue text is short and usually doesn't name the file, so search is the hard part.
- Hints won't help: 129/129 are empty.
- About 10% of tasks look out of reach inside 32k tokens and about 5 min (inferred).

**How the hidden set differs.** About 120 tasks from private repositories, evenly split public and private; the public half is exactly 58 tasks (CR L43–44). No training repo appears in the test set (CR L45, staff). So none of the fastapi-specific patterns or file names transfer. Do not treat the numbers above as hidden-set numbers, only as the best available shape. The dev set is only 4 repos, and fastapi and rich are 89% of it.

## 5. Context and token limits

- **Window:** 32,768 tokens for prompt, reasoning and output combined (README L166).
- **Compaction:** interval 15, overlap 2, token threshold 14,336, retention 5 (README L571–574). This is set in the harness, and no submission key changes it. Note that 14,336 + 16,384 (default `max_output_tokens`) + 2,048 = 32,768, so the defaults look designed to fit together (inferred). **Keep `max_output_tokens` at 16,384 or below.**
- **Caching:** `min_tokens` 2,048, TTL 1,800 s, intervals 10 (README L576).
- **Output caps:** `run_command` stdout and stderr 5,000 chars each; `read_file` 150 lines and 10,000 chars; graph tools 5,000 chars (README L390, L444, L497, L507, L522).
- **Truncated tool calls:** an unclosed `<|tool_call>` or `MAX_TOKENS`/`LENGTH` gets a nudge; up to 3 consecutive empty turns, a 4th ends the session (README L358–367). Nudges reset whenever a turn has a tool call.
- **Thinking:** default 4,096 (README L148). The note recommends `include_thoughts: true` + `thinking_budget` and omitting `thinking_level` (L149). Secondary: disabling thinking went 48→23, hiding summaries −16, budget changes ≤3 tasks (CR L161–162).

**Choices that follow.**
- `temperature 0.2`, `thinking_budget 4096`, `include_thoughts: true`, `max_output_tokens 16384`. Don't tune temperature first; ablations show noise (CR L162).
- Prompt: pipe tests through `| tail -40` and use `--tb=short` so failures fit in 5,000 chars.
- Prompt: split big edits, never paste a file back (README L684).
- Put `{problem_description}` in the root instruction so the issue survives compaction (README L301; inferred). Max issue 10,095 chars, about 3k tokens.
- **Do not write `{hints}` in a template.** It is only set when non-empty (README L299), and it is empty on 129/129 dev tasks, so a template reference may fail. ADK has an optional `{hints?}` form, but ADK isn't here to check (inferred).
- Don't put literal `{...}` code samples in instructions: ADK may read them as template variables (inferred, unverified).

## 6. Graph tools

**Stored form** (computed: one graph for the schema, 25 tasks for the text-versus-source comparison, all 129 for coverage).
- Nodes have `id`, `name`, `text`; edges have `key`, `source`, `target`, `type`, and the only edge type seen is `calls`. Graph files are named `<repo>_<base_commit>.json` (127 files; 129 tasks all map to one).
- **Nodes have no file path or line numbers.** `docs_src` paths lose their prefix, e.g. `path_operation_configuration.tutorial005_py310.Item`, so the agent has to turn a dotted name into a path itself.
- `text` is source. Functions are mostly verbatim: 264 same, 20 differ in a 284-sample check. Classes are stubs: 5 same, 137 differ. For example `class Item(BaseModel):\n    None` and `ServerSentEvent` 737 chars versus 3,276 in source.

**Coverage of gold symbols.**
- 482 of 544 changed symbols are nodes (88.6%): `def` 398/406, `class` 78/80, **`async def` 6/58**. Across the same files: `async` 43/502 are nodes, `def` 4,739/5,024, `class` 855/858.
- Task level: all changed symbols present 95, some 19, none 6, nothing to find (new file or module-level only) 9.
- The host note says async is missing and private tasks touch none, so private graphs were not updated (CR L131). So the async gap may not matter on the hidden set; unverified.

**Usefulness.**
- `get_code_neighbors`: median 4 edges on gold symbols; 30 of 482 have none (10 of them `def`). OK for "who calls this?" after you have a symbol.
- `search_similar_code` looks up a symbol name, then returns nearest neighbours; it does not embed free text (README L506). From a gold symbol, on average only 16% of the nearest 10 are in the same module and 29% are tests. In 34 of 58 multi-symbol tasks, some gold symbol has another gold symbol in its nearest 10 (computed).
- `get_code_subgraph`: needs symbols you already have. I did not test its output.
- 224,589 of about 370,700 nodes (61%) are from `tests` (computed).
- My own emulation of the lexical fallback (issue words matched against node id words; **not the real code**): a gold module in the top 10 nodes for 48 of 114 tasks, and 73 of 114 if test nodes are excluded. Top-1: 22 of 114. Fine as a hint, weak as a primary search.
- Public ablations found no gain from graph or semantic search (CR L133, L165, secondary).

**Verdict.** Don't make these the first search. Grep is more direct. Keep at most `get_code_neighbors` for caller checks. Test removing all three, which also shrinks the tool list (secondary: the strongest public bundles did, CR L151).

## 7. Agent architecture

Allowed by README L105–125: `LlmAgent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent` (`max_iterations` 1–500, default 500); `agent_tool` with `skip_summarization`; `sub_agents`; `output_key`; `include_contents`.

- **Sequential locate-then-fix** works by design: analyzer with `output_key: plan`, then coder with `{plan}` in its instruction (README L116, L112). Each agent costs model calls against about 5 min. Secondary: analyzer gained 1 task, top public bundles were single-agent (CR L150, L164).
- **`LoopAgent`:** no `exit_loop` among the 9 registered tools (README L373) and callbacks are closed (README L69). So a loop cannot end early by itself. Set `max_iterations` small (2–3) if used at all (inferred).
- **`ParallelAgent`:** branches share one `/workspace`; no benefit for one patch (inferred).
- **`AgentTool` + `skip_summarization`:** keeps file reads out of the root's context (README L690). In ADK, `skip_summarization` marks the event as final, so the root's turn likely ends after the tool returns and the harness sends a "Normal stop" nudge (README L367; inferred from memory of ADK, its source isn't here). Test before relying on it.
- **Skills:** `load_skill`, `load_skill_resource`, `run_skill_script` (README L353; CR L63). Extensions conflict: the user reports the overview says Python or bash; README L144 allows `.py` only (`.sh` is not on the list). Could not read the overview; CR doesn't mention bash. **Use `.py` only.** Whether scripts count against `max_tool_calls`, where they run and which interpreter is used are all unstated.
- **Best opening (inferred):** single root agent, 6 tools (`run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`), plus `get_code_neighbors` if testing shows value.

## 8. Model choice

**What the docs state.**
- Four allowed QAT models, one per submission (README L174–177, L181).
- Weight footprint: 31B about 16–18 GB, 12B about 6–8 GB, E4B about 3–4 GB, E2B about 2–3 GB, on 4×L4 with about 86 GB usable (README L165, L174–177).
- Staff: smaller models run under the same conditions (CR L30).
- E2B/E4B bonus is $10k; best small-model public score was 0.10 on 2026-10-30, against 0.29 overall on 2026-11-02 (CR L32, L38, L75).

**Public evidence.** 31 local tasks: 31B solved 9–11, 12B about 4, E4B 0, and 12B was not faster per task (CR L168, secondary). Small sample.

**Unknown, must be measured.** Tokens per second for each model on 4×L4. Nothing in the README gives speed.

**Recommendation.** Main pick 31B; second final pick E4B or E2B, since private score is the better of two picks (CR L46). PB L13 chose 12B; that decision should be revisited (see Questions).

## 9. LoRA

**Allowed.** Rank up to 128 (README L183; L169 sets it to the max detected rank), under 3 GiB unpacked in total, `.safetensors` only, `adapters/<name>/` with `adapter_config.json` and `adapter_model.safetensors`, names matching `[A-Za-z0-9][A-Za-z0-9._-]*` (README L134, L145, L206). Different adapters per agent are allowed, on one base model (README L205). Size planning for 31B: r=16 about 110–220 MB; r=128 about 0.9–1.8 GB (README L211–214).

**Where to train.** Scoring is offline (README L254, CR L50). Training itself is not ruled on in the README. Interactive L4×4 notebooks exist and use quota at 2× (CR L50). 31B in QAT form won't fit on 16 GB with training overhead (inferred); 12B, E4B and E2B might.

**Training data.** The 129 dev tasks have gold patches, and `swegemma eval` writes full ATIF traces (README L674). So traces could be collected, or synthetic ones built from gold patches (inferred). Limits: 4 repos, so it risks learning those repos instead of the skill. Drop rich trajectories that read outside `/workspace`, because `rich-15.0.0` in the wheels has upstream fixes (CR L173; wheel seen in `wheels\`). Mixed reports on benefit (CR L170).

**Unknowns.**
- Staff say train against unquantized weights (CR L30). The README is silent; the sample config names the QAT base as `base_model_name_or_path` (Sample `adapter_config.json` L4). Whether an unquantized-trained LoRA behaves well on W4A16 weights is unverified.
- Whether vLLM on this checkpoint needs a specific target-module layout: the sample's module names are `model.language_model.layers.<i>.self_attn.{q,o}_proj` (computed), but no working non-dummy example is in the dataset.
- Whether LoRA speeds or slows inference on 4×L4.

**Likely best use, if any (inferred).** Valid short tool calls and short thinking, not repo knowledge.

## 10. Local evaluation

- `swegemma eval` needs `--tasks`, `--snapshots-dir`, `--submission-dir`, `--results-dir` (README L639–648), an inference server (vLLM on `:8000`), and the `swebench-sandbox:latest` image (README L253).
- **The packages are only described, not present.** `wheels\` has 124 wheels of dependencies (`fastapi`, `pydantic`, `pytest`, `rich`, `starlette`, etc.) but no `swegemma`, `adk_submission`, `adk_eval_core`, `google-adk`, `vllm` or `litellm`. CR L29 mentions a "wheelhouse", presumably on Kaggle. Needs checking with a logged-in user.
- `Dockerfile.public` (`docker\`) can build the image using the local wheels (`docker\Dockerfile.public`). Not tried.
- **User's PC** (inferred from README footprints; hardware: RTX 5070 Ti with 16 GB as you stated, and checked here: 31.8 GB RAM, WSL2 distros and Docker 28.3.0 present, about 26 GB free on each of C: and D:):
  - 31B: weights alone (16–18 GB) don't fit in 16 GB, so it will not serve properly here.
  - 12B (6–8 GB), E4B, E2B should fit with a smaller context cache. Real speed unknown.
  - Good for debugging the harness, prompts and tool use. Results won't equal 31B on 4×L4.
  - `--concurrency 2` is fine for RAM with 4 GiB containers (inferred).
  - Disk is tight: 26 GB free on D: and only 26.7 GB on C:. A 31B checkpoint and Docker image will need room.
- Plain notebook runs can fail gold tests from missing test deps; 52/129 pass plain, 127/129 in a scorer-like sandbox (CR L141, secondary). Don't trust a plain Python local eval.

## 11. Conflicts and ambiguities

| Topic | One says | Other says | What to do |
|---|---|---|---|
| Skill script types | README L144: `.py` only | User reports overview says Python or bash (could not read it) | `.py` only |
| Declarative security | README L28, L69: no competitor Python | README L144: `.py` skill scripts allowed | Assume scripts run in the sandbox; test |
| Tool count | README L30, L373: 9 tools | README L353, CR L63: skill tools exist too | Skill tools are additional |
| `pytest.ini` / `conftest.py` | README L290, L686: edits appear in `agent_patch` | README L591, L615: they are stripped | Either way, don't touch |
| Patch base | README L407, L588: `_swegemma_baseline` | README L688, mermaid: `git diff HEAD`; L240 `git diff HEAD` | Never `git commit` |
| `verification_timeout_seconds` | CR L51 lists it for `eval_config` | README L560: fixed at 300 s, no key | Assume fixed |
| `max_turns` default | README L556: 500 | CR L51: none | Set it yourself |
| Test edits | Sample `prompts/system.md` L32: auto failure | README L615: stripped | Stripped; don't do it anyway |
| Search input | Sample `prompts/system.md` L11: keywords | README L506: symbol path, keyword only as fallback | Symbol names |
| Model list | CR L31: README "reportedly" 31B-only | README L174–181: all four listed now | CR is stale; four are allowed |
| Graph/embedding count | CR L130, L132: 256 files each | Folders here hold 127 each, named `<repo>_<commit>` | Current data is 127 |
| Graph path | README L490: `data/graphs/<repo>.json` | Actual `graphs\<repo>_<commit>.json` | Use actual names |
| 12 h and setup | CR L48: 12 h includes setup | README L566: `max_time_minutes` excludes setup | Budget setup separately |
| Graph vs `async def` | README silent | CR L131 host: missing; computed: 43/502 present | Don't rely on graph for async |
| Model plan | PB L13: develop on 12B | CR L168 secondary: 12B about 4/31, 31B 9–11/31 | See Questions |
| Over 12 h | PB L36 states scores zero | CR L53 marks it secondary | Treat as true, not verified |

---

## Unknowns that need measuring

1. Scorer concurrency, vLLM start-up time, and per-task setup time (nothing in README).
2. Real tokens per second for 31B, 12B, E4B, E2B on 4×L4.
3. Whether a model call can overrun `max_time_minutes`.
4. Whether a prompt larger than the window minus `max_output_tokens` is clamped or rejected by vLLM.
5. Whether `skip_summarization` ends the root agent's turn in this harness.
6. Whether skill scripts count as tool calls, where they run, and whether a `.sh` is rejected.
7. Whether `{hints}` fails when `hints` is absent; whether `{hints?}` works.
8. Whether `_swegemma_baseline` exists, and what happens if the agent commits.
9. Whether a LoRA trained on unquantized weights applies correctly to the QAT checkpoint.
10. Whether removing graph tools helps or hurts on the real board.
11. The real behaviour of `search_similar_code`'s lexical fallback (my emulation is only an approximation).
12. Whether the hidden set is really free of `async def` changes (rests on a host post via CR).

## Questions for the user

1. Are you OK signing in to Kaggle yourself to re-check the Overview and Evaluation pages? They could not be read here, so every Kaggle fact above is via `competition-rules.md`.
2. Can you get `swegemma` and `adk-submission` from the starter notebook or wheelhouse? Without them no local run is possible. They aren't in the dataset.
3. PB L13 says develop on 12B; you now want to win the main track. Should the main pick move to 31B, with 12B/E4B as second pick? (Recommended: yes, but check speed first.)
4. Distillation from external LLMs is allowed per an admin (CR L171), but your scope rule says official sources only. Keep it excluded?
5. Is outside compute for LoRA training OK under your scope rule, or Kaggle notebooks only?

---

## Round 2 (2026-11-09)

**New sources.** **NB** = official starter notebook and its run log, as pasted by the user. **SBM** = small-model leaderboard (Kaggle staff notebook, updated 2026-11-07 23:58 UTC, as pasted). **computed** = my read-only scripts over `tasks.jsonl`, `snapshots\` (read in memory), `embeddings\` and the sample adapter header, run with `python -I`. Round 1 names (README, CR, Sample, PB) unchanged.

**Blocked again.** Plain fetches of the competition Overview and the Kaggle Gemma 4 models page on 2026-11-09 each returned only a title. Tried once each, as asked. I did not use Kaggle's internal API, an account, or any login. So Kaggle facts still come through CR, NB and SBM.

**Corrections to Round 1 (dated 2026-11-09).**
- §5 "Keep `max_output_tokens` at 16,384 or below": still true, but too loose. At about 60 tokens/s (§F), 16,384 tokens is about 270 s, nearly a whole 5-minute task on one turn. Use 4,096–6,000 (inferred).
- §1 "`get_status` … The prompt should use it": it is free against `max_tool_calls` (README L417), but each call still costs a model turn, about 7–13 s on 12B (§F, inferred). Check once at most.
- §1 worst-case formula assumes every task hits the cap. That is the safe bound, not the expected time. See B2.
- §11 row `verification_timeout_seconds`: NB parsing does accept this key (plus `max_llm_calls`, and a top-level section when `evaluation:` is absent). README L560 says fixed at 300 s on the scorer. Assume fixed; do not rely on it.
- §10 "packages only described, not present": still true of `D:\AI Project\gemma-4-developer-agent\wheels\`, but NB shows a 41-wheel Kaggle dataset, `/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse`, with the harness.
- **Code note.** `pilot.gold_files` matches only `diff --git` headers. All 129 dev patches use `--- a/` and `+++ b/` headers only, so it returns nothing on this dataset (computed). I used my own header parser for gold files. `pilot.py` itself is untouched, and the ranking rules were unchanged. If anyone reuses `pilot.gold_files` on these tasks, fix it first.

### A. What the leaderboards imply

**Scores in tasks on 58 (floor to 2 decimals, computed).**

| Score | Tasks | Where |
|---|---|---|
| 0.12 | 7 | small-model top, one team (SBM) |
| 0.10 | 6 | 15 teams (SBM) |
| 0.08 | 5 | through rank 89 (SBM) |
| 0.06 | 4 | next group (SBM) |
| 0.15 | 9 | main median, 2026-11-02 (CR L78) |
| 0.24 | 14 | main 2nd–9th (CR L76) |
| 0.29 | 17 | main top (CR L75) |

- Next steps up: 8 tasks = 0.13, 9 = 0.15, 10 = 0.17. To lead the small board today: **8/58, +1 task**. Top grew from 0.10 on 2026-10-30 (CR L38) to 0.12 on 2026-11-07: +1 task in 8 days.
- Tie-break on equal private scores: unknown here.

**Noise (computed, binomial, 58 tasks).**

| True rate | sd of score, tasks | public minus private, sd in tasks |
|---|---|---|
| 0.10 | 2.3 | 3.2 |
| 0.20 | 3.1 | 4.3 |
| 0.29 | 3.5 | 4.9 |

- Picking between two agents on the same 58 tasks: paired, so only tasks where exactly one succeeds count. If 15% of tasks differ, sd of the difference is 2.9 tasks. A true +2 gain shows higher in 71% of runs, +3 in 83%; if 20% differ and the gain is +5, 93% (computed).
- Surprise: if 170 small-model teams all had a true 8% rate, the expected public top is 11/58 (computed). The real top is 7. So the small-model spread is tighter than pure noise: teams solve largely the same easy tasks, and small models hit a ceiling (inferred). More variants of the same approach won't reach past it.

**Private split.** Public is 58 (CR L44); private is about 62 if the total is about 120 (inferred). Same task-sampling noise, so a public lead of 1–2 tasks means little. Simulation (rough; assumes each team's true rate equals its public score):

| Our true rate | P(first, small board, field as today) | field +0.02 by Dec |
|---|---|---|
| 0.14 (8/58) | 13% | 5% |
| 0.16 (9/58) | 24% | 11% |
| 0.20 (12/58) | 53% | 34% |
| 0.25 (15/58) | 83% | 67% |

| Our true rate | P(first, main board at 2026-11-02) |
|---|---|
| 0.29 | 7% |
| 0.36 | 36% |
| 0.40 | 60% |

**Plain answer.** The E2B/E4B bonus is the most reachable prize. Target **12–15 tasks on an E-model** for about even-to-better odds. For the main top, about 23/58. Those are similar task gains, but the bonus field is smaller, its best is 7, E-models iterate cheaply (runs at home, see §G), and 31B is expensive to test. Main-track prize places other than first are unknown here; if a place like 3rd pays well, the 31B slot could still be worthwhile, and it costs one final pick anyway.

### B. Attacking the premises

**1. "31B is the best main-slot model given 6 minutes per task."** Observation if false: 12B or smaller near the main top, or 31B too slow to finish many turns in 6 min. Evidence: 12B output about 60 tok/s from NB log (§F). 31B speed unmeasured (Round 1 §8). If 31B scales with size, about 23 tok/s (inferred), giving about 7k output tokens in 5 min: only about 6 turns at 4,000-character thoughts, which would be starved. Public 31B bundles reach 0.24 with 8 min/28 calls (CR L152), so reality is better than that scaling or thoughts are shorter. "6 minutes" is also the unsafe number: 120 × 6 = 720 min, exactly the 12 h limit, with no margin for start-up or setup. **Verdict: cannot test yet; weak.** Measure 31B and 12B tok/s on one prompt in one notebook first (step 2 of the plan).

**2. "Tasks are scored serially, so 120 × budget must fit 12 h."** Observation if false: a large budget finishes in much less wall time. Evidence: NB runs `evaluate_task` in a serial for-loop, but only for 2 notebook tasks; README L656 `--concurrency` exists but is the CLI. CR L168 8-min 12B timed out (secondary); CR L152 8 min/28 calls scored 0.24 (secondary): that does not contradict serial, because bundles rarely use their whole cap. **Verdict: cannot test yet; holds as planning assumption.**
Cheapest experiment, one submission (1 day, 1 queue slot):
   - Model E2B. Prompt: "Call `run_command` once with `sleep 115`, then call `submit_patch`. Do nothing else." `eval_config`: `max_time_minutes: 2`, `max_tool_calls: 5`, `timeout_seconds: 120`.
   - Expected score 0.00. Read the notebook's elapsed runtime on the submission page. Serial: about 120 × 2 min + start-up ≈ 4 h. Concurrency 4: about 1 h. Elapsed runtime also gives start-up plus setup per task: T − 120 × 1.9.
   - If the submission page doesn't show runtime (inferred it does), fall back to a 7-minute version of the same prompt: 120 × 7 = 14 h fails if serial, passes if concurrent. Costs up to 12 h of queue and one slot, so try the 2-minute form first.
   - Risk: a small model may not always call `sleep`, which only lowers the time estimate; compare with the session minimum.

**3. "The model must do its own localization."** Observation if false: a deterministic ranker alone finds gold files often. §D: Hit@1 32%, Hit@3 52%, Hit@5 63%, Hit@10 78% on 128 tasks, using stdlib-only rules not tuned on this data. **Verdict: weak.** The ranker can't replace the model: in 37% of tasks no gold file is in its top 5. But a top-5 list given before the first model turn should cut wandering (NB Task 1 spent all 10 calls without an edit). Keep the model in the loop to confirm.

**4. "Building up from the official sample is the best route."** Observation if false: stronger results come from other shapes. NB log: 2/2 NO_PATCH at sample budgets, 5–10 calls with no edit. Sample-shape baseline scored 0.08 (CR L82, secondary); top public bundles were single-agent with no graph tools (CR L150, L151, secondary). **Verdict: false as a route, valid as a schema example.** Start from a single agent and a short prompt.

**5. "LoRA should come last."** Observation if false: an early LoRA gave a measured gain on the small board. No such measure exists here. Some claim LoRA at the top, others report none (CR L170, secondary). For the main slot: **holds**. For the E-slot: **weak**: a small model's main failure may be tool-format and looping, which is what a LoRA could change, and E-model training fits at home. **Cannot test yet** without a real LoRA.

**6. "Graph and embedding tools are not worth their tokens."** Numbers (computed, 3 commits per repo; 1,500 sampled nodes per commit, 200 queries for nearest neighbours):

| Repo | Pair cosine median (p5–p95) | Mean top-5 cosine | Share of top-5 pairs ≥0.99 | Top-1 minus top-10 cosine |
|---|---|---|---|---|
| fastapi | 0.835–0.840 (0.35–0.996) | 0.997–0.998 | 93–95% | 0.0026 |
| rich | 0.934–0.936 (0.71–0.995) | 0.997–0.999 | 97–98% | 0.0027 |
| requests | 0.911–0.917 (0.57–0.996) | 0.995–0.998 | 93–95% | 0.0047 |
| httpx | 0.941 (0.60–0.998) | 0.996 | 98% | 0.0047 |

   So a similarity of 0.999 means almost nothing: near-duplicate clusters give it to most queries. Do not let the model read that number as confidence. But the embeddings are not noise: same-module share in the top 10 neighbours is 15% fastapi, 32% rich, 35% requests, 47% httpx, against random-pair base rates 0.3%, 2.2%, 17%, 4.8%. Neighbour order is informative, the scores are not. Cost: up to 5,000 chars (about 1,300 tokens) per call (README L507). Search needs a symbol name, which the model usually lacks (README L506; Round 1 §6). **Verdict: holds as a first-search tool; weak as "never use".** Possible niche: find sibling implementations once you have a symbol. A/B it only after the core works.

**7. "One long agent run per task beats a fixed pipeline."** Observation if false: planner-then-editor beats a single agent, measured. Public evidence favours single-agent (CR L150, secondary), analyzer +1 (CR L164, secondary). At 12B speed each extra agent costs model calls against about 18k output tokens (§F). NB Task 1 shows a pure long run can wander with no edit. **Verdict: cannot test yet; weak.** Hybrid is the cheapest try: a single agent with a forced first step (localizer output).

**8. "More tool calls and more time always help."** Observation if false: returns flatten after some cap. Secondary ablation: 50→25 calls cost 14/129 (CR L163). But at 12B speed 300 s fits about 22–43 calls (§F), and a 28–40 cap is not binding on most runs. Compaction: interval 15, retention 5, threshold 14,336 (README L571–574). If an event is one model response or one tool result, compaction runs every 7–8 calls (inferred), so 3–6 times per task, and each drops detail and probably costs a model call (inferred, ADK not here to check). "Always" fails at the 12 h cap: 5 min per task leaves 2 h for start-up and setup; 6 min leaves none. The per-task budget doesn't roll over between tasks (inferred). **Verdict: false as "always"; holds up to about 5 min and a 40-call cap for now.**

### D. Deterministic localizer on the 129 dev tasks

Method: `extract_keywords` and `rank_files` from a copy of `pilot.py`, frozen weights. Pool: `.py` files from each snapshot through `run.py`'s `is_source` filter (no tests, test, testing, docs, examples, vendored packages). Gold: non-test source files in the reference patch that exist at base. Dropped: 1 task whose gold was only new files, so n = 128. 0 tasks had no source gold at all. Per-file hits are per-gold-at-all (one gold file in top k).

| Set | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 |
|---|---|---|---|---|---|
| All | 128 | 32.0% | 52.3% | 63.3% | 78.1% |
| fastapi | 66 | 24.2% | 50.0% | 62.1% | 81.8% |
| rich | 48 | 27.1% | 43.8% | 56.2% | 66.7% |
| requests | 13 | 84.6% | 92.3% | 92.3% | 100% |
| httpx | 1 | 1/1 | 1/1 | 1/1 | 1/1 |

- docs_src: 15 tasks have gold files there. If docs_src is removed from pool and gold (n = 125): Hit@1 32.8%, Hit@3 52.8%, Hit@5 65.6%, Hit@10 78.4%.
- First gold file rank: median 3; 4 of 128 tasks: no gold file scored at all.
- Size matters: median pool 739 files fastapi, 87 rich, 19 requests, 32 httpx. Requests is easy because it is small.
- Runtime: median 1.1 s, p90 4.2 s, max 9.9 s (extract plus rank, this PC, Python 3.10; 2 vCPU in the scorer likely similar, inferred).
- Rules were tuned on other data, so this is not contaminated. Do not tune them on this data.

**Shipping as a skill.** Logic is `re`, `math`, `json` only, so a `.py` works. README L144 allows `.py` (not `.sh`). README L353 mentions `run_skill_script` only for argument coercion; **no README text on how scripts get arguments, where they run, or their time or tool-call cost**. Round 1's unknown #6 stands. I recall ADK's script tool needing a code executor (from memory, ADK source not here; (inferred)). Unknown whether the script can see `/workspace`.
Safe fallback (inferred): no skill; prompt the agent to write the ranker to `/tmp/loc.py` then run `python3 /tmp/loc.py` with the issue. About 800–1,100 tokens to copy, so about 13–18 s on 12B plus one tool call. Worth testing against the skill route.

### E. Training data inside the official data

**Git history (computed, in memory, newest snapshot per repo; ≤3-file limit is on non-test, non-docs_src source files).** Across all snapshots the commit SHAs union to the newest snapshot's set, so history is fully deduplicated. All of these are aggregate counts only.

| Repo | Commits | Non-merge | Touch source | Source and tests | Fix-looking | Usable (either) | Usable, ≤3 source files | 1 source file |
|---|---|---|---|---|---|---|---|---|
| fastapi | 7,353 | 7,339 | 963 | 333 | 226 | 428 | 370 | 268 |
| rich | 4,449 | 3,378 | 1,880 | 521 | 414 | 797 | 671 | 496 |
| requests | 6,475 | 4,862 | 2,250 | 333 | 373 | 609 | 579 | 484 |
| httpx (1 task) | — | — | — | — | — | not counted (loose objects, single 1.6 MB snapshot) | | |

Total usable: 1,834 (≤3 source files: 1,620). "Fix-looking" is a message pattern match; expect some noise.

**Caveats.**
- `tasks.jsonl` `base_commit` does not match the snapshot SHAs (0 of 125 checked were found): history was rewritten by `fast-export`/`fast-import` (README L268). So my direct "dev fix is in history" count failed. Since every snapshot's commits are inside the newest snapshot, every dev task older than the newest has its fix inside the newest history (inferred). **Training on a repo's history leaks dev-task fixes for that repo.**
- So: train only on repos excluded from any evaluation you trust, and the sealed repo must not be used at all. If rich is sealed (§G), usable = fastapi plus requests = 1,037 commits, and dev scores on fastapi/requests become biased if trained on them. Train on one repo, evaluate on the other, or only compare LoRA by the hidden board.
- Commit subjects are terse, not issue-like. A trace would need a synthetic issue from the subject and test diff. Limited to 3 repos: risk of learning those codebases.

**Could this make few-shots?** Yes: a few short traces in the prompt (about 1–2k tokens each) from non-sealed repos. Cheaper than LoRA, testable at once.

**Training route.**
- Trainable checkpoint: staff say train on unquantized weights at `kaggle.com/models/google/gemma-4/transformers` (CR L30, primary via CR; page unreadable here). README L178 lists bf16 `gemma-4-31b-it`, `gemma-4-12b-it`, `gemma-4-e4b-it`, `gemma-4-e2b-it`. So yes for the E-models, by name; availability on Kaggle not confirmed directly.
- Sample adapter header (computed): 4 tensors, BF16, rank 4, layer 0 only, `q_proj` `lora_A` [4, 5376] and `lora_B` [8192, 4], `o_proj` `lora_A` [4, 8192] and `lora_B` [5376, 4]. So the 31B text hidden size is 5376, and the attention projection is 8192 (computed). `target_modules` q_proj, o_proj; `layers_to_transform` [0]; `r` 4; `lora_alpha` 8. Sample's `base_model_name_or_path` is the QAT name. This explains NB's stripping of adapters on other models: shapes don't fit (inferred).
- `max_lora_rank = max(detected_ranks)` (README L169), so low-rank adapters are cheap, with a ceiling of 128 (README L183).
- Does a LoRA trained on non-QAT weights apply to `-qat-w4a16-ct`? **Unknown.** Math: a delta added on `q_proj`/`o_proj` should load if the module names match, but behaviour on quantized weights is untested. Cheapest test: load a non-dummy, known adapter on a QAT checkpoint in a notebook; check it loads, and that outputs change.
- What fits on 4×L4 with quota: inference is what those GPUs do best; bf16 31B footprint is at the top of README's `~4–62 GB` range (inferred), about 15 GB per GPU, tight with gradients. Interactive use bills at 2× (CR L50). E2B/E4B training at home on 16 GB is the realistic route (inferred), and fits the scope question below.

### F. Time and token arithmetic

**12B speed (NB log, inferred).** Thoughts of 4,400 chars in 19 s and 4,050 in 18 s: 225–232 chars/s. At 3.5–4 chars per token (assumed): **about 60 tokens/s** (58–66), with time to first token included.

| At 60 tok/s | Tokens |
|---|---|
| 5 min, generating only | 18,000 |
| 5 min, 20% tool and overhead time | about 14,000 |
| 1 thought at budget 4,096 | 68 s |
| `max_output_tokens` 16,384 on one turn | 273 s |

Observed per-call time, sample budgets: 7.0 s (Task 1: 70.2 s/10 calls) and 13.5 s (Task 2: 67.3 s/5). So 300 s fits about 22–43 calls. Time, not `max_tool_calls` (40), is the limit.

**`thinking_budget` on 12B.** The two thoughts seen were about 1,100–1,250 tokens, under the 4,096 budget, so 4,096 did not bind them. A budget is a ceiling, not a target. Set **2,048** as the hard cap (about 34 s worst case) and tell the prompt to keep thinking to a few sentences on most turns. Round 1 and CR say thinking on helps (CR L161); budget size itself ≤3 tasks (CR L162, secondary). Keep `include_thoughts: true`. Set `max_output_tokens` about 4,096 (room for thinking plus a small edit); split large edits.

**Artefacts.** `Okay, I<image|>The user wants` in thought and `<|cha...` in visible text (NB log). If visible text ends a turn without a tool call, it counts as a text-only turn (README L358–367): a wasted turn (7–13 s) and a nudge; 3 in a row plus one more ends the session. Effect on score unknown. Measure from traces: share of turns with these strings and share of those with no tool call. `stop_sequences` is **not** a fix: `<|channel>` must appear for thinking to work, and a stop on the text would truncate turns (inferred). Do not add prompts that echo these tokens.

**Other models.** No speed evidence. 31B, E4B and E2B: measure before tuning. Cheapest way: in one notebook, one fixed prompt with a known length, time to first and last token, for each of the four models (about 30 min of L4x4 time).

### G. Notebook as evaluator

**What a session gives.** NB shows `Evaluator.evaluate_task` works in a Kaggle notebook. Per task at a 5-min budget: 5 + setup and verification (about 1–2 min, unknown) ≈ 6.5 min, about **9 tasks/h serial**. A 12-h session (Kaggle limit; not verified on the competition page) minus 20 min start-up: about 105 tasks. CR L50 says L4x4 interactive uses quota at 2×; CR L187 reports 30 h/week (secondary), so about 15 real hours/week, **about 135 tasks/week**, if those hold. Save-and-run commits may bill differently: unknown.

**Dev budget.** With rich sealed: 81 dev tasks ≈ 8.8 h per pass, under 2 passes a week. So use a fixed 40-task subset (26 fastapi, 13 requests, 1 httpx; choose the fastapi tasks at random and record them) to compare candidates, full pass only for shortlisted ones. ≈ 4.5 h per comparison per candidate.

**Sandbox differences that can mislead (README §4.1, CR, Dockerfile.public).**

| | Notebook `sandbox='subprocess'` | Scorer Docker | Effect |
|---|---|---|---|
| CPU, memory | shared, no 4 GiB/2 vCPU limit | 4 GiB, 2 vCPU | tests that pass here may OOM or time out there |
| Network | whatever the notebook has | `network_mode=none` | set notebook internet off |
| Python | 3.12 (NB) | 3.13-slim (Dockerfile.public) | small test differences |
| Paths | `/workspace`, `/tmp` rewritten at shell level | real paths | absolute-path tricks behave differently |
| Test deps | venv from wheels | sandbox image | **52/129 vs 127/129 gold passes in other participants' runs** (CR L141, secondary) |
| Timing | no parity with scorer model load or queue | scorer | use time budget from a real submission |

**Required calibration:** before scoring anything, run all dev gold patches through the verify step and record the pass count under `subprocess`. Expect roughly the 127/129 scorer-like figure if `subprocess` reproduces it; if not, use only tasks whose gold passes. Concurrency via CLI `--concurrency` is possible (README L656) but distorts per-task time, so only use it for call-capped runs with a very high `max_time_minutes`.

**Home on the 16 GB RTX 5070 Ti (WSL2).** Likely yes for E2B/E4B/12B (footprints README L175–177) using the wheelhouse plus Docker sandbox and `Dockerfile.public` (Round 1 §10). This is closer to the scorer than the notebook's subprocess sandbox. Needs: download of the 41 wheels and model weights by the user (Kaggle login); a Python 3.12 environment plus torch and CUDA; disk is tight (26 GB free per drive). Results differ in speed from 4×L4 (TP=1, probably faster per token, inferred), so match **output tokens per task**, not seconds: measure the scorer's tok/s from one real run and set the local `max_time_minutes` so tokens match. Whether the 41 wheels install cleanly outside Kaggle is unknown.

**Which repo to seal: rich** (48 tasks).
- Requests (13) and httpx (1) are too few: sd of a 13-task score at 30% is about 13 points. Also requests is small and easy (Hit@1 85%).
- fastapi (67) is 52% of the dev set. Sealing it leaves too little to tune on, and 15 of 67 tasks have gold in `docs_src`, an oddity of this repo.
- rich: enough tasks (sd about 6 points at 20%), a different domain from web frameworks, 87 source files, short issues (median 138 chars), Hit@1 27%, 37/48 single-gold-file. Similarity to hidden repos is unknown: only 4 dev repos, and the hidden set is private (CR L43).
- Known defect: `rich-15.0.0` in wheels holds upstream fixes (CR L173, secondary). When scoring the sealed set, drop any task whose trace reads `site-packages/rich`, and report how many.
- Decision is the user's. Results above are aggregates; no rich-specific rule was made.

### H. Ideas worth trying

Gains are rough (inferred) tasks on 58 for an E-model unless noted. Test = A/B in the 40-task notebook set, then one real submission.

| Idea | Expected gain | Cost (days) | Risk | Test |
|---|---|---|---|---|
| Set `max_time_minutes` 5, tool-call cap 40, thinking 2,048, output 4,096 | Required; stops NO_PATCH from budgets | 0.25 | low | 2-task notebook |
| Forced early edit: prompt "first edit by call 12" (CR L153) | +2–4 | 0.5 | premature edit; keep tests to confirm | 40-task A/B |
| Localizer first (skill or `/tmp/loc.py`) | +1–3 | 1–2 | skill route unknown; token cost of copying | A/B, plus check `/workspace` access |
| Test-first repro in `/tmp` | +0–2 | 0.5 | eats calls on small models | A/B on calls and time |
| Whole-file test run before submit (Round 1 lever 3) | +1–2 | 0.25 | test time; use `--tb=short`, `| tail -40` | A/B |
| Skill toolkit: compact test output, diff check | +1–2 | 1–2 | as above | notebook smoke |
| LoopAgent (`max_iterations: 2`) with fallback "apply best edit now" sub-agent (README L124) | +0–2 | 1 | a loop can't end itself (Round 1 §7); second iteration only if first didn't submit | smoke, then A/B |
| Sequential planner then editor with `output_key` | -1 to +2 | 1–2 | doubles model calls at low tok/s | A/B on 12B and E4B only |
| `include_contents: none` editor after a plan | 0–+2 | 1 | loses context if plan is thin; ADK behaviour | A/B |
| Read-only analyzer via AgentTool, `skip_summarization` | 0–+1 (CR L164) | 1 | may end root's turn (Round 1 §7) | smoke first |
| Few-shot traces in prompt (non-sealed repos only) | +1–3 | 1–2 | prompt cost 1–2k tokens each | A/B |
| Generic bug-class checklist (no repo names) | 0–+1 | 0.25 | filler | A/B |
| Fixed `seed` and `temperature` 0.2 | reproducible runs; 0 gain | 0 | none | check two runs match (CR L85) |
| Omit `{hints}` from prompt, not `{hints?}` | avoids possible template error | 0 | none. Harness adds hints to user message when present (README L313) | none needed |
| `get_status` at most once | 7–13 s saved per skipped call | 0 | small | none needed |
| Fewer tools: 6 tools (Round 1 §7) | +0–2 | 0 | loses graph hints | A/B |
| `stop_sequences` for artefacts | not advised | — | truncates turns | do not ship |

**Not proposed, and why:** editing tests or test config (stripped by the harness, and against the spirit of the rules); reading other teams' files or hidden data; any `.py` skill that reads outside `/workspace` for task data. If in doubt, ask.

### Best plan in order

1. **Nov 9–10.** Run the serial/timing experiment (B2) as the next submission. It uses one daily slot, and gives scorer start-up, setup and concurrency.
2. **Nov 10–11.** Fork NB. Time all four models on one prompt. Run gold-patch calibration under `subprocess`.
3. **Nov 11–12.** Choose the sealed repo (recommended: rich, §G). Fix the 40-task subset from the rest. Do not change it afterwards.
4. **Nov 12–14.** Single agent, 6 tools, short prompt, forced early edit, whole-file test before submit, `eval_config` 5 min/40 calls, thinking 2,048, output about 4,096. Submit on **E4B** as the first bonus candidate.
5. **Nov 13–17.** Stand up home WSL2 + Docker for E2B/E4B if the user agrees (§G). Match tokens to the scorer's tok/s.
6. **Nov 15–19.** A/B the localizer (skill and `/tmp/loc.py`) on the subset. Keep whichever wins, or none.
7. **Nov 17–21.** A/B few-shots, test-first repro, and a LoopAgent fallback, one at a time, on the subset. E4B vs E2B on the best config.
8. **Nov 21–24.** Same best config on 31B (or 12B if timing says so), with a real budget from step 2. Submit one for the main slot.
9. **Nov 22–26.** Optional LoRA trial for the E-slot only if steps 4–7 stall, on repos not used for evaluating it. Skip if behind.
10. **Nov 26–28.** Full pass on the dev set, then one run on the sealed repo. Use once; no tuning after.
11. **Nov 28–30.** Final submissions early because of 14–33 h queue waits (CR L58) and one pending slot (CR L57).
12. **Nov 30–Dec 2.** Pick finals: best E-model entry and best overall entry. Stop all changes by Dec 1.

### Unknowns that need a real run

1. Serial vs concurrent, scorer start-up, setup per task (step 1).
2. tok/s for 31B, E4B, E2B on 4×L4; whether 12B's about 60 tok/s holds across prompts.
3. Gold-patch pass rate under `subprocess` vs the 127/129 figure.
4. Share of turns with `<|channel>` or `<image|>` artefacts, and whether they cost a nudge.
5. Whether `run_skill_script` sees `/workspace`, how it takes arguments, and what it costs.
6. Whether compaction spends a model call and how much context it loses.
7. Whether a non-dummy LoRA loads and changes output on a `-qat-w4a16-ct` checkpoint.
8. Whether the 41 wheels install outside Kaggle and run on one GPU.
9. Notebook session limit, weekly quota and whether Save-and-Run bills at 2×.
10. Tie-break rule on equal private scores.

### Questions for the user

1. Seal rich? Recommended (§G), with the `rich-15.0.0` wheel caveat noted there.
2. Internal Kaggle API (used in earlier notes for CR) is the way to re-check official pages without login. I did not use it this round, as you asked for one plain try. Do you want it used, or will you re-check the Overview and Evaluation pages yourself?
3. Home setup: OK to install torch and CUDA in WSL2 and download the wheelhouse and E-model weights yourself? These are competition assets plus standard tooling.
4. Outside benchmarks or datasets: none used. Few-shots and LoRA from the snapshots stay inside official data. Still OK if training uses git-history commits rather than dev tasks?
5. The main-prize split between places (only the $65k total is in my notes): can you check it on the Prizes page? It decides how much effort goes to the 31B slot.
6. Can you confirm whether 30 h/week and the 12-h session limit are right for L4x4?
