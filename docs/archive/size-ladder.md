# Size-ladder viability: where does a small Gemma 4 break as a localization query-writer?

Date: 2026-11-02. This note builds on `research/novelty-survey.md` and does not repeat it. Proposed paper: Gemma 4 E2B, E4B, 12B and 26B-A4B, all untrained. Each model makes one call per issue to write search keywords, and the pilot's ripgrep scorer stays frozen. The paper measures Hit@k per size to find where performance collapses, then tests cheap fixes.

Legend:
- **[V]** I read the primary page (arXiv abstract/HTML, HF card, official repo or docs) this session.
- **[D]** I computed it this session from the HF parquet files, using `datasets-server` and `resolve/main` downloads.
- **[S]** It comes from a search snippet or a secondary site.
- **[U]** It is from memory, or is my own estimate. Check it before citing.

---

## 0. Two facts that change the plan

1. **Gemma 4's training-data cutoff is January 2025, not the 2026-03-31 release date.** The model card says "with a cutoff date of January 2025" [V, ai.google.dev/gemma/docs/core/model_card_4]. Issues created from Feb 2025 on are therefore post-cutoff, and that already covers about 750 curated Python issues (section 3). A strict post-*release* slice (after 2026-03-31) exists, but it is small: 65 Python issues in SWE-rebench [D], plus about 300+ non-Python issues in SWE-bench-Live MultiLang [D].
2. **The pilot's K2 already gives Gemma the repo file list.** So the "file-tree hint" arm is really *full list vs. pruned tree vs. none*. On large repos, the full list is the main cost: Django has thousands of `.py` paths [U on exact count], which is tens of thousands of prompt tokens. At E2B/26B prefill speeds, that dominates runtime.

## 1. Prior size-scaling work on localization / SWE sub-tasks

| Work | Sizes | Setting | Finding | Same as proposed? |
|---|---|---|---|---|
| SWE-MERA (arXiv:2507.11059) [V HTML, Tables 2/4] | Qwen2.5-Coder-Instruct 7B / 14B / 32B | Aider agent, end-to-end; "localize files" = % of attempts that identify the files to fix | 2025 split: 58.2 → 86.0 → 86.3%. 2024 split: 68.8 → 85.0 → 91.5% | **Closest size curve.** It shows a knee between 7B and 14B, but it is agentic, has no fixed retriever, tests no fixes and uses only three sizes |
| Co-PatcheR (arXiv:2505.18955) [V HTML, App. C.2] | Qwen2.5-Coder 7B / 14B / 32B, **fine-tuned** | File-tree → file localization (Top@5) | Bigger is better, but 32B ≈ 14B (the numbers are only in Fig. 6b) | No. The models are trained, and no fixes are tested |
| Lasbordes et al. (arXiv:2610.05099) [V HTML] | Untrained Qwen3-1.7B, MiniCPM5-1B, LFM2.5-1.2B; untrained Qwen3-32B | Multi-turn grep/colgrep agent | Lite File-F1: 1.7B grep 18.75, 1.7B colgrep 34.51, 32B colgrep 63.50. **No 4–14B points, and no few-shot or voting** | No. It is two endpoints, not a ladder, the agent is multi-turn, and the fix is training |
| Chavan (arXiv:2609.23742) [V HTML] | 0.6B–4B (Qwen3, Llama-3.2, Phi-4-mini) | 14 generic JSON/extraction tasks, constrained decoding (Outlines, XGrammar) | Constrained decoding makes schema validity 100% everywhere. A semantic gap stays at 0.6B (5.7 pts). 1B+CD (0.986) > 3B unconstrained (0.777) | Not SE, but **directly predicts the JSON/grammar arm** |
| LocAgent (arXiv:2503.09089) [S] | 7B distilled from 32B | Graph agent | Fine-tuned 7B ≈ Claude-3.5 on Loc-Bench | No (trained) |
| EffGen (arXiv:2602.00887) [S] | Qwen2.5-Instruct 7B–32B | SWE-bench Lite resolution | 0.67% → 2.33% | No (resolution, not localization) |
| Bug Attention Probe (arXiv:2502.13966) [S] | Llama-3.2-1B and up | Line-level FL with probes | A probed 1B beats prompted large models | No (different task) |
| SWE-bench Illusion (arXiv:2506.12286) [V abstract] | Frontier models | File path from issue text alone | Up to 76% on Verified vs. ≤53% on non-SWE-bench repos | It is the contamination probe to reuse |

**Answer to Q1.** I found **no study that holds the retriever fixed, sweeps the query-writer's size within one open family, and then tests which inference-time fixes recover the small end.** The nearest work is SWE-MERA (3 sizes, agentic, no fixes), Lasbordes (2 untrained endpoints, then training) and Chavan (a constrained-decoding size study on non-SE tasks). I also found no published SWE-bench localization result for any Gemma 4 model [S; search came up empty]. The per-size failure point plus fix-recovery study therefore looks **not done**. The usual caveat applies: absence in search is not proof.

## 2. Evidence for each candidate fix

| Fix | Prior evidence | Expected effect on E2B/E4B | Novelty of testing it |
|---|---|---|---|
| **Schema-constrained JSON** (Ollama `format: <schema>`) | Chavan 2026: CD removes structural failures at 0.6–4B but leaves semantic errors [V]. Tam et al., "Let Me Speak Freely?" (arXiv:2408.02442, EMNLP'24 Industry): JSON mode hurts *reasoning* but can help classification and extraction [S]. The pilot needed a broken-JSON parser fix at 12B, which moved Hit@1 from 69 to 80 together with the dotted-name split | **High at E2B** if parse failures are common. Near zero at 12B+. Keyword listing is extraction, so the Tam penalty should be small | Low. It is well known; report it as the hygiene baseline |
| **Instructed JSON vs. constrained JSON** | Ollama docs say `format` "enforce[s] a JSON schema" [V]. That it uses llama.cpp grammar-constrained sampling is [U] | Separates "the model can't follow the format" from "the model writes bad terms" | Low–medium. In Ollama, "structured output" and "grammar decoding" are the **same knob**, so merge these two arms into one |
| **Few-shot** | The fault-localization empirical study (arXiv:2510.20521) finds that 1–3 shots help task structure and format, with diminishing returns, on mid/large API models [S]. It is broadly well known | Moderate at E2B/E4B. Risk: small models copy identifiers from the examples. Use examples from repos outside the eval set and measure the copy rate | Low |
| **Self-consistency / voting** (k samples, frequency-weighted keyword union) | Wang et al. self-consistency (arXiv:2203.11171) [U details]. AutoFL uses SC for LLM fault localization (via Lachesis, arXiv:2412.08281) [S]. Small models are less self-consistent (arXiv:2505.17656) [S], so voting has more variance to remove | **Probably the strongest fix for small models.** It also acts as query expansion, which helps weak query-writers (next row). Cost is k× calls | Medium. It is known in general, but not measured for keyword generation × size |
| **Rule + LLM merge** | Weller et al. (arXiv:2309.08541, EACL Findings'24): over 24 retrievers, expansion helps weak systems and hurts strong ones [V snippet+S]. query2doc (arXiv:2303.07678) keeps the original query alongside the generated text: +3–15% BM25 [V abstract]. The pilot: a naive merge *hurt* 12B (80 → 73) | **Predicted crossover:** the merge rescues E2B and hurts 12B/26B. Merge only the rules' code identifiers, not plain words | **Medium–high.** A measured crossover size is a concrete, new, Gemma-specific finding that explains the pilot's negative result |
| **File-tree hint** (none / pruned dirs+filenames / full) | Agentless localizes from the repo tree [V abstract]. Compact trees cut tokens by about 41% with equal path recovery (arXiv:2606.11976) [S]. RepoNav: a tree scaffold beats an inline one (arXiv:2609.08355) [S]. Caumartin et al. (arXiv:2607.11046): file paths alone are a weak representation [V] | Helps path keywords, but small models may hallucinate files, and on big repos it costs the most prefill | Medium. "How much tree does each size need" is new, but secondary |
| **Test-failure re-query** | Established: FaR-Loc, OrcaLoca, AutoCodeRover (see the survey). The pilot's gain was about 3 issues | Needs test execution (Docker per instance) or leaks the gold `test_patch` | **Low. Drop it from the minimum set,** or report it as an oracle upper bound |

**Ranking by likely recovery of E2B/E4B** [U, my judgment]: voting ≥ identifier-only rule merge > constrained JSON (only if parse failures exist) > few-shot > tree pruning > test re-query. **Most novel to report:** the rule-merge crossover and the voting-vs-size curve. **Least novel:** JSON/grammar, few-shot, test re-query. Present those as controls.

## 3. Datasets (gold file lists = files touched by the gold `patch`)

Counts marked [D] were computed from the HF parquet this session. "Post-cutoff" means created after 2025-01-31 (Gemma 4 cutoff); "post-release" means created after 2026-03-31.

| Dataset (HF id) | Size | Repos | Lang | Created range | Post-cutoff / post-release | Gold patch | License |
|---|---|---|---|---|---|---|---|
| SWE-bench Lite (`princeton-nlp/SWE-bench_Lite`) | 300 test (+23 dev) [D] | 12 [D]; django 114, sympy 77 | Python | 2012-09 → 2023-07 [D] | 0 / 0 | `patch`; all single-file [D] | No license tag on HF [D]; repo MIT [U] |
| SWE-bench Verified (`princeton-nlp/SWE-bench_Verified`) | 500 [D] | 12 [D] | Python | 2013-01 → 2023-08 [D] | 0 / 0 | `patch`; 85.8% single-file [D] | No tag [D] |
| SWE-bench-Live (`SWE-bench-Live/SWE-bench-Live`) | full 1,888; test 1,000; lite 300; verified 500 [D] | 223 (full) [D] | Python | to 2025-09-02 [D]; frozen since the Sep-2025 update [V GitHub] | 805 / 0 [D] | `patch`, `base_commit` [V]; 40% single-file, 3.4 files mean [D] | MIT [V] |
| SWE-bench-Live MultiLang (`SWE-bench-Live/MultiLang`) | 1,077 in 8 language splits [D] | 431 [V GitHub] | C, C++, C#, Go, Java, JS, TS, Rust | to 2026-07-31 [D, 4 of 8 splits read] | ≈all / ≥298 in 4 splits [D] | `patch` [V] | MIT [V] |
| **SWE-rebench leaderboard** (`nebius/SWE-rebench-leaderboard`) | 860 (monthly splits 2025_01…2026_03) [D] | 413 [D] | Python | 2025-01-03 → **2026-05-12** [D]. The "2026_03" split holds 43 Apr + 21 May 2026 issues [D] | **754 / 65** (373 / 51 repos) [D] | `patch`, `base_commit`, `created_at`, docker image [D]; 43% single-file, 59% touch only `.py` [D] | CC-BY-4.0 [V] |
| SWE-rebench full (`nebius/SWE-rebench`) | 21,336 test + 6,542 filtered [D] | 3,400+ [V] | Python | 2014-04 → 2025-04 [V viewer] | few / 0 | `patch`, `base_commit` [V] | CC-BY-4.0 [V] |
| SWE-bench Multilingual (`SWE-bench/SWE-bench_Multilingual`) | 300 [D] | 41 [D] | 9 languages, no Python | 2017-02 → 2025-03 [D] | 2 / 0 [D] | `patch` [D] | MIT [D] |
| Multi-SWE-bench (`ByteDance-Seed/Multi-SWE-bench`) | 1,632 [V]; mini/flash ≈400/300 [U] | 33 [V] | 7 languages, no Python | not on card | unknown | `fix_patch`; `base` is a branch object [V] | CC0 (+ByteDance IP caveat) [V] |
| Loc-Bench V1 (`czlll/Loc-Bench_V1`) | 560 [D] | 165 [D] | Python (83% `.py`-only gold) | 2015-11 → 2025-02-07 [D] | ≈0 | `patch`, plus `edit_functions` (function-level gold) [D] | No tag [D] |
| SWE-bench Pro (`ScaleAI/SWE-bench_Pro`) | 642 default + 51 hard (1,424 rows total) [D] | multi [U] | multi (`repo_language`) [D] | unknown | unknown | `patch`, `base_commit` [D] | No tag [D] |
| SWE-Gym (`SWE-Gym/SWE-Gym`) | 2,438 train [D] | 11 [D] | Python | 2018-09 → 2024-05 [D] | 0 / 0 | `patch`; 41% single-file [D] | MIT [D] |
| SWE-smith (`SWE-bench/SWE-smith`) | 59,136 [D] | 128 [U] | Python | synthetic | n/a | Injected bugs with LLM-written issues. **Unsuitable** for realistic localization | MIT [D] |

Notes:
- **Gold-file definition matters.** In SWE-rebench and SWE-bench-Live, 40–45% of gold patches touch non-`.py` files (changelogs, `pyproject.toml`, docs) [D]. Define gold = touched *non-test source files in the searchable set*. Drop instances with an empty gold set, and report how many were dropped.
- 9 of the pilot's 55 instances are in Lite and Verified [D]. Exclude them, or report them separately, because they were the rule-tuning set.

### Recommended evaluation set (~600 issues, Python, one GPU)

- **Set A, comparability and contaminated (300):** SWE-bench Lite test minus the 9 pilot instances, which leaves 291. It is directly comparable to published file Hit@1 (Agentless, LocAgent, Caumartin & Melo, Lasbordes). It has only 12 repos, so cloning is cheap. Report a per-repo macro average too, because Django is 38% of the set [D].
- **Set B, post-cutoff and clean (~300):** SWE-rebench leaderboard, issues created from 2025-02-01. Take **all 65 post-release issues** (Apr–May 2026, 51 repos) plus a repo-stratified sample of about 235 from Feb 2025–Mar 2026, capped at ≤2 issues per repo. That gives many repos and limits SQLGlot/SymPy dominance (41 and 28 issues in the full set [D]). Repos are fetched shallowly at `base_commit` (`git fetch --depth 1 origin <sha>`). About 300 repos at roughly 10–30 s each takes a few hours [U].
- **Contamination check:** (i) the per-size Hit@1 gap between A and B; (ii) the Illusion-style memorization probe (file path from issue text alone, no tree, no grep) on A vs. B; (iii) the 65-issue post-release slice as a sanity line. Its 95% CI is about ±12 pts, so it is not a headline.
- **Skip for this paper:** MultiLang and Multi-SWE-bench. The `def`/`class` bonus is Python-specific, and their C/C++/Java repos are large to clone. Mention them as future work.

## 4. Feasibility on RTX 5070 Ti 16 GB via Ollama

Ollama tags [V, ollama.com/library/gemma4/tags]:

| Model | Params (card) [V] | Tag → size | Fits 16 GB? |
|---|---|---|---|
| E2B | 2.3B effective (5.1B with embeddings) | `e2b-it-q4_K_M` 4.6 GB; `e2b-it-qat` 4.3 GB; `e2b-it-q8_0` 6.0 GB | Yes |
| E4B | 4.5B effective (8B with embeddings) | `e4b-it-q4_K_M` 6.6 GB; `e4b-it-qat` 6.1 GB; `q8_0` 9.0 GB | Yes |
| 12B Unified | 11.95B | `12b-it-q4_K_M` 8.0 GB; `12b-it-qat` 7.2 GB; `q8_0` 13 GB | Yes (Q4/QAT) |
| 26B-A4B (MoE) | 25.2B total / 3.8B active | `26b-a4b-it-qat` **16 GB**; `26b-a4b-it-q4_K_M` 18 GB; `nvfp4` 16 GB (MLX only) | **No, not fully.** The weights alone are ≥16 GB before the KV cache, so Ollama splits across GPU and CPU |
| 31B | 30.7B | `31b-it-qat` 19 GB | No |

- **26B-A4B will run partly offloaded.** Only 3.8B parameters are active per token, so CPU-side expert compute is tolerable. An estimate (not a measurement) puts Q4_K_M at about 53 tok/s on a 5070 Ti with partial offload [S, modelfit.io]. I'd plan for **15–40 tok/s** generation and slow prefill [U]. If Ollama is too slow, llama.cpp's MoE-expert CPU offload (`--n-cpu-moe` / `-ot ...exps=CPU`) keeps attention on the GPU [U]. **Measure on day 1** with `ollama ps` and `eval_count/eval_duration`.
- **Use the QAT tag for every size** so quantization is matched across the ladder. All four sizes have one [V].
- **Turn thinking off** (`think: false`) and use T=0 for the single-call baseline. Gemma 4 has "configurable thinking modes" [V Ollama page]. Whether `think:false` is honored for gemma4 is [U]: check `/api/show`. The recommended sampling is T=1.0, top_p 0.95, top_k 64 [V], which suits the voting arm.
- **Throughput budget** [U, estimates]. Assume a prompt of about 1.5k tokens with a pruned tree (not the full file list) and about 150 output tokens. Then rough seconds per call are E2B ~1, E4B ~1.5, 12B ~3, and 26B-A4B ~6–10. With 600 issues and about 10 calls per issue per size (baseline, JSON, 3-shot, k=5 voting, 2 tree variants; the merge needs no call), that is 6,000 calls per size. The total is roughly 6,000 × (1 + 1.5 + 3 + 8) s ≈ **22 GPU-hours**. A full file list on Django-size repos could multiply prefill cost several times, so cap the tree at about 4k tokens. Ripgrep scoring is CPU-only and negligible. Five days is enough, with slack for one rerun.

## 5. Verdict

**Viable, and novel in a narrow but defensible way.** The building blocks are known (survey, plus section 2 here). The measured *per-size failure point with fixed retrieval, plus a fix-by-size recovery matrix for an untrained open family* is not in the literature I found. It is directly relevant to on-device Gemma 4 dev agents, because it tells a builder which size and which cheap trick to ship.

**Defensible contribution (one sentence):** On about 600 multi-repo Python issues, including about 300 created after Gemma 4's January 2025 training cutoff, we find the smallest untrained Gemma 4 model whose single-call search keywords beat a zero-parameter rule extractor under a frozen ripgrep localizer. We attribute each size's misses to format, term-choice or hallucination errors, and show which inference-time fixes (voting, rule merge, constrained JSON, few-shot, tree pruning) recover the small models, at measured cost on a 16 GB consumer GPU.

**Minimum credible experiment set:**
1. Data: Set A (291 Lite) + Set B (~300 SWE-rebench post-cutoff, including all 65 post-release). Rules, prompt and scorer are frozen before Set B is touched.
2. Floors: random, BM25 on the raw issue, K1 rules (0 params), and the memorization probe per size.
3. Ladder: E2B, E4B, 12B, 26B-A4B, QAT, thinking off, T=0.
4. Fixes, one factor at a time at every size: constrained JSON (also logs the parse-failure rate), 3-shot (out-of-set examples), voting with k=5, identifier-only rule merge, and tree none/pruned. Then one best-combination row per size.
5. Metrics: file Hit@1/3/5, plus diagnostics: parse failures, the % of keywords with zero rg hits (hallucination), the % copied from few-shot examples, output tokens, latency, VRAM. Use paired bootstrap 95% CIs and McNemar tests against the K1 rules. At n=300, a Hit@1 near 50% has a CI of about ±5.7 pts, so effects under ~5 pts will not be resolvable.
6. One figure: Hit@1 vs. size, one line per fix, with the K1 and BM25 floors as horizontal lines, for Set A and Set B side by side.

**Main risks:**
- **No cliff.** E2B may already beat the rules because the scorer does most of the work. Mitigation: frame it as "the scorer makes size matter less", with the cost curve as the result. That is still useful.
- **26B-A4B offload** is slow or forces a different quantization. Mitigation: QAT everywhere, and measure on day 1. If needed, drop to three sizes plus 26B on Set B only.
- **Contamination on Set A.** Lean on Set B for claims, and use A only for comparability.
- **Gold-set noise** from multi-file and non-source patches. Define gold strictly, and report the dropped count.
- **The pilot's rules were tuned on requests/flask.** Freeze them now, and don't retune on Set B.
- **Large repos inflate prompt size** through the file list, and the def-bonus favors Python. Prune the tree and stay with Python.
- **Novelty critique:** each fix is individually known. The answer is the interaction with size, especially the predicted merge crossover. State plainly that the fixes themselves aren't new.
- **Schedule:** 10 days to the deadline, with about 5 GPU days. A data pipeline for about 300 new repos is the main engineering risk. Start the clones first.

## Sources

Primary, read this session:
- Gemma 4 model card: https://ai.google.dev/gemma/docs/core/model_card_4
- Ollama tags: https://ollama.com/library/gemma4/tags and https://ollama.com/library/gemma4
- Ollama docs: https://docs.ollama.com/capabilities/structured-outputs and https://docs.ollama.com/capabilities/thinking
- arXiv: 2507.11059 (HTML v3); 2505.18955 (HTML); 2610.05099 (HTML); 2609.23742 (HTML); 2506.12286 (abs); 2303.07678 (abs)
- SWE-bench-Live: https://huggingface.co/datasets/SWE-bench-Live/SWE-bench-Live, https://huggingface.co/datasets/SWE-bench-Live/MultiLang and https://github.com/microsoft/SWE-bench-Live
- SWE-rebench: https://huggingface.co/datasets/nebius/SWE-rebench and https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard (parquet read directly)
- Other datasets: https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench and https://huggingface.co/datasets/SWE-bench/SWE-bench_Multilingual
- Statistics read via the HF datasets-server API: `princeton-nlp/SWE-bench_Lite`, `princeton-nlp/SWE-bench_Verified`, `czlll/Loc-Bench_V1`, `SWE-Gym/SWE-Gym`, `SWE-bench/SWE-smith`, `ScaleAI/SWE-bench_Pro`

Secondary or snippet only:
- arXiv: 2408.02442; 2309.08541; 2510.20521; 2412.08281; 2505.17656; 2606.11976; 2609.08355; 2503.09089; 2602.00887; 2502.13966; 2203.11171 [U]
- Estimates: https://modelfit.io/can-i-run/gemma4-26b-a4b-q4-on-rtx-5070-ti/ (estimate) and https://computingforgeeks.com/rtx-5070-ti-vs-5060-ti-local-ai/
