# Novelty survey: small-model keywords + grep for issue-to-file localization

Date: 2026-11-02. Scope: is the pilot (`pilot/README.md`, `pilot/results/results.md`) novel enough for a 3,000-word Kaggle paper-track submission?

Pilot recap: Gemma 4 12B (local, Ollama) reads the issue plus the repo file list and lists search terms. The terms are scored with whole-word grep (`weight × (log(1+hits) + def_bonus) × idf`), and the top-k files come back with ±10-line windows. On 55 SWE-bench issues (44 requests, 11 flask), Hit@1 is 80% for Gemma keywords (K2), 69% for rule keywords (K1) and 58% for whole-file BM25 (B1). Mean lines opened in the top 5 are 1,030 for K2 and 2,999 for BM25.

Verification legend: **[V]** means I read the primary source page (abstract or HTML) this session. **[S]** means the claim comes from a search snippet or a secondary source, not the full paper. **[U]** means it is from memory or unverified, so check it before citing.

---

## 1. LLM-based localization in SWE-bench agents

| System | How the issue becomes a search | LLM keywords + grep? | Compared against BM25? |
|---|---|---|---|
| SWE-bench baseline (Jimenez et al., ICLR 2024, arXiv:2310.06770) [U] | The whole issue is a BM25 query over whole files | No | It *is* the BM25 baseline |
| SWE-agent (NeurIPS 2024, arXiv:2405.15793) [S] | The LLM issues ACI commands "to locate filenames and strings within files or directories" (`find_file`, `search_dir`, `search_file` [U]). Iterative search scored 12.0%, below no search at all (15.7%) [S] | **Yes, implicitly.** The LLM picks the strings it greps for | No localization-vs-BM25 study |
| AutoCodeRover (ISSTA 2024, arXiv:2404.05427) [V] | The LLM calls AST-aware search APIs (`search_class`, `search_method`, `search_code` [U]) with names it extracts from the issue. Spectrum-based fault localization from tests narrows context when tests exist [V] | **Close.** LLM-chosen identifiers go to structural search, not plain grep | No |
| Agentless (arXiv:2407.01489) [V abstract; method details S via arXiv:2607.11046] | The LLM picks files from the repo tree, prunes irrelevant folders, then embedding retrieval (text-embedding-3-small); results are combined into the top files | No. Tree prompt plus embeddings | Embeddings, not BM25 |
| Moatless Tools (github.com/aorwall/moatless-tools) [S] | AST, vector index (Voyage embeddings) and file-system operations | Partly. Semantic queries come from the LLM | No |
| OrcaLoca (ICML 2025, arXiv:2502.00350) [V] | A priority-queue agent over `search_file_contents`, `search_class`, `search_callable` and similar tools. A "plain text parser" pulls suspicious keywords from the issue. A reproducer agent seeds the start from traceback frames | **Yes, the keyword-extraction step exists.** It feeds structural search, run with Claude 3.5 Sonnet only | No |
| CoSIL (ASE 2025, arXiv:2503.22424) [S] | LLM-driven search over a call graph, with a pruner. Top-1 is 43% on Lite and 44.6% on Verified with Qwen2.5-Coder-32B | No | No |
| LocAgent (arXiv:2503.09089) [V] | An agent over a heterogeneous code graph with search and traverse tools. Its fine-tuned Qwen2.5-Coder 7B and 32B release Loc-Bench and an 86% cost cut | Its graph search tool does keyword matching over entities [U] | It reports retriever baselines, BM25 among them [U] |
| BugCerberus (arXiv:2502.15292) [S] | Three fine-tuned LLMs work at file, function and statement level | No | Reports the best file-level Top-1/3 on Lite |
| SweRank (ICLR 2026, arXiv:2505.07849) [S] | A bi-encoder retriever plus a listwise LLM reranker, trained on SweLoc. File Acc@1 is 83.2, against LocAgent 78.5 and SWE-Fixer 69.7. SweRankEmbed-Small (137M) beats 7B embedders. SweRank+ (arXiv:2512.20482) adds a multi-turn agent | No. The issue text is the dense query | Yes, it beats BM25 and others |
| RepoGraph (arXiv:2410.14684) [U] | Ego-graph retrieval around a line-level code graph, plugged into agents | It uses keyword search over graph nodes [U] | Not as a headline |
| SWE-Fixer (ACL Findings 2025) [S] | BM25 retrieval, then an LLM picks files | No (raw BM25) | BM25 *is* its retriever |
| **Caumartin & Melo, "Reformulate, Retrieve, Localize" (BotSE 2026, arXiv:2512.07022)** [V] | **Local Qwen3-30B-A3B via Ollama fills a JSON schema (summary, paths, filenames, identifiers, snippet, stack trace, error). The fields become a BM25 query over files.** An agent then reranks | **Yes, LLM-extracted keywords, but fed to BM25, not grep** | **Yes.** SWE-bench Lite Hit@1 rises from 0.400 to 0.476 (BM25 raw vs. best reformulation). The agent reaches 0.727. LCA rises from 0.320 to 0.440 |
| Caumartin, Chen & Costa (arXiv:2607.11046, July 2026) [V] | Compares code *representations* (paths, raw code, LLM summaries) under lexical, semantic and LLM retrieval. Role-aware summaries give +40% Hit@5 over paths with a 10–21× smaller footprint | No (this varies the document side) | Yes, lexical retrieval included |
| **Lasbordes et al., "Small Agents with Semantic Search" (arXiv:2610.05099, Oct 2026)** [V] | **1–1.7B models (Qwen3-1.7B and others) are trained with SFT and RL to write grep and colgrep queries.** File-F1 on Lite for the Qwen3-1.7B grep agent is 18.75 at base, 50.13 after SFT and 63.75 after RL. A BM25 oracle top-10 scores 53.67 | **Yes. Small models generating grep queries, multi-turn** | Yes. A BM25 top-10 row is included. They report tokens and latency |
| CodeScout (arXiv:2603.17829, Mar 2026) [V abstract; S tool details] | RL-trained code-search agents using only a Unix terminal (rg + sed per its model card [S]). The 14B model reaches Lite File-F1 of about 72 [S] | **Yes. LLM-driven ripgrep** | Unknown |
| Fattha et al. (arXiv:2606.11976, Jun 2026) [V] | Linear vs. domain-scoped parallel exploration with a Haiku-class model. It plots methods against a "BM25 envelope" [S] | Partly | Yes, via the envelope plot |
| SHERLOC (arXiv:2606.24820) [S] | A single reasoning LLM. Lite file Acc@1 is 84.33% with DeepSeek-R1, and it stays competitive at about 30B | No | Unknown |

**Bottom line for Q1.** The idea "an LLM turns the issue into search terms, then a lexical engine searches" is **well established**. SWE-agent, AutoCodeRover and OrcaLoca do it inside agents. Caumartin & Melo 2025 do exactly "a local open LLM extracts identifiers and keywords, then lexical retrieval, then a measured gain over raw-issue BM25." Lasbordes et al. 2026 do "small (<2B) models write grep queries, compared against BM25, with token accounting." The pilot's specific combination is not claimed by any paper I found. That combination is a *single-shot* keyword list from an *untrained* ~12B model, scored by a fixed grep scorer (log-hits, idf, def/class bonus), returning line windows. It is an engineering variant, not a new idea.

## 2. Query reformulation for IR-based bug localization

Pre-LLM:
- BLUiR (Saha, Lease, Khurshid, Perry, ASE 2013) [S]: structured IR that indexes class and method names separately. This is the conceptual ancestor of the pilot's def/class bonus. https://ischool.utexas.edu/ml/papers/saha-ase13.pdf
- Locus (Wen, Wu, Cheung, ASE 2016) [S]: localizes at the change-hunk level and adds history boosting. https://cse.hkust.edu.hk/faculty/scc/publ/ase16-Locus-preprint.pdf
- Chaparro, Florez, Marcus, "Using Observed Behavior to Reformulate Queries during TR-based Bug Localization," ICSME 2017 (Distinguished Paper) [S]. Cooper et al., EMSE 24(5) 2019, find that the title plus observed behavior is the best reduced query [S]. https://par.nsf.gov/servlets/purl/10120539
- Rahman & Roy, BLIZZARD, "Improving IR-Based Bug Localization with Context-Aware Query Reformulation," ESEC/FSE 2018, arXiv:1808.00594 [S]. It classifies reports as noisy (stack traces), rich (code) or poor, and reformulates each class differently. **This is the closest pre-LLM analogue of the pilot's typed rule extractor (K1: path, ident, error and word weights).** Their STRICT keyword extraction (SANER 2017) is relevant too [U].
- Rahman & Roy, systematic review of query reformulation in code search, arXiv:2108.09646 [S].
- Wong et al., segmentation plus stack-trace analysis (ICSME 2014) [U], and Moreno et al., Lobster (stack traces) [U]: stack-trace terms boost localization.

LLM era:
- BRaIn (arXiv:2501.10542) [S]: LLM relevance feedback rewrites the query, then BM25 (Elasticsearch), then a rerank.
- IQLoc (arXiv:2510.04468) [S]: semantics-driven query *reduction*. BM25 top-K, then a cross-encoder, then a reduced query. About +42% HIT@1 over baseline queries.
- Caumartin & Melo (arXiv:2512.07022) [V]: see above. This is the most direct prior work.
- Generation-augmented code search: ReCo, "Rewriting the Code" (Li, Zhou, Shen, ACL 2024, arXiv:2401.04514) [V]. It generates exemplar code to expand a query for sparse and dense retrieval. HyDE (Gao et al., arXiv:2212.10496) is the general-IR origin [U].

**Bottom line for Q2.** "Reformulate the bug report into a better lexical query" is a roughly 10-year-old research line. "Use an LLM to do it" has had at least three papers since 2025. The pilot's K1 rules recreate BLIZZARD-style typed extraction. Do not claim query reformulation as new.

## 3. Small/local/open models (<15B)

- Qwen3-1.7B, MiniCPM5-1B and LFM2.5-1.2B trained to search (arXiv:2610.05099) [V]: *untrained* 1.7B grep agents are poor (Lite File-F1 18.75), and training fixes them. They found that untrained small models handle multi-turn agent search badly.
- Lingma SWE-GPT 7B, FileHit about 58.8% on Lite, against 19.2% for base Qwen2.5-Coder-7B-Instruct (Table III of arXiv:2506.12728) [S].
- LocAgent fine-tuned Qwen2.5-Coder-7B (huggingface.co/czlll/Qwen2.5-Coder-7B-CL) [S].
- CodeScout includes sub-15B RL models [S], and SweRankEmbed-Small has 137M parameters [S].
- SWE-Gym 32B reaches 20.6% resolved on Verified with OpenHands [S, via arXiv:2506.07636]. Lingma SWE-GPT 72B reaches 32.8% [S]. SWE-smith (arXiv:2504.21798) trains a 32B agent [U]. A Klear-Agent-8B on SWE-smith trajectories is listed at 39.0% [S, third-party README, unverified].
- Gemma 4: E2B, E4B, 26B A4B and 31B shipped on 2026-03-31; 12B "Unified" followed on 2026-06-03 (ai.google.dev/gemma/docs/releases) [S]. **I found no published SWE-bench localization result for any Gemma 4 model.** [S; absence of evidence from search]

**Gaps for small quantized models:**
1. Almost all small-model localization work *fine-tunes* (SFT or RL) or uses a trained retriever. Prompted, untrained, quantized models as *one-shot query generators* (not multi-turn agents) are barely measured. 2610.05099 suggests base models are weak as agents, which makes "a single call is enough" an interesting contrast.
2. No paper I found runs a model-size ladder of one open family as the *query generator only*, with retrieval held fixed.
3. No paper I found reports Gemma 4 results, or measurements on consumer hardware (latency, VRAM) for localization.

## 4. Test-failure output to refine localization

- AutoCodeRover [V]: spectrum-based fault localization from tests, when tests exist.
- OrcaLoca [V]: a reproducer agent captures VizTracer traces, an LLM keeps up to 5 frames, and those seed the search. Only 38% of issues reproduced.
- CoSIL's comparison credits OrcaLoca's strong 7B top-1 partly to reproduction tracebacks [S].
- Classic LLM fault localization from failing tests (Defects4J style): AutoFL (arXiv:2308.05487), LLM4FL (arXiv:2409.13642), FaR-Loc (arXiv:2509.20552, which turns the failing test and stack trace into a retrieval query), SieveFL (arXiv:2605.13491), and stack-trace fine-tuning (arXiv:2501.18005) [all S].
- Pre-LLM: stack-trace-boosted IR localization (BLIZZARD's "noisy" class, Wong 2014) [S/U].
- Agentless uses reproduction tests for *patch selection*, not localization [U].

**Bottom line for Q4.** "Re-query with failing-test text" is established (FaR-Loc is nearly the same idea). The pilot's retry result is also weak: Hit@3 rises from 91% to 96% with Hit@1 unchanged, which is about 3 issues. Keep it as a minor, honest ablation, not a contribution.

## 5. Verdict

### What is already done (blunt)
- An LLM extracts keywords or identifiers from the issue, lexical retrieval follows, and it beats raw-issue BM25. **Done:** Caumartin & Melo 2025 (local Qwen 30B, Ollama, SWE-bench Lite, Hit@1 0.400 → 0.476).
- An LLM drives grep/ripgrep for localization. **Done:** SWE-agent, CodeScout, and Lasbordes et al. 2026 (with BM25 comparisons and token accounting, at sub-2B).
- Keyword extraction feeding structural search. **Done:** OrcaLoca, AutoCodeRover.
- Definition-aware ranking. **Done in spirit:** BLUiR (2013).
- Re-query with failing tests or traces. **Done:** OrcaLoca, FaR-Loc, AutoCodeRover.
- The pilot's headline (Gemma beats BM25 on Hit@1) is **expected**, not surprising, given this literature.

### Narrow gap the pilot could credibly claim
"**One call, no training, no agent loop:** how small can the query-writer be? A fixed grep scorer lets a quantized ≤12B model localize as well as multi-turn agents, at a fraction of the tokens and lines read." No paper I found isolates the *query generator's size* with retrieval held fixed, for an untrained model in a single call, measured in Hit@1 per token and per line opened. Gemma 4 has no published localization numbers, so the Gemma-specific measurements are new data by default. That is weak novelty on its own but directly relevant to the competition.

### Concrete framings and experiments that would make it defensible
1. **Size ladder (the main result).** Run E2B, E4B, 12B and 26B-A4B (optionally 31B) as keyword generators, with the scorer frozen. Plot Hit@1 against model size, generated tokens, wall-clock time on consumer GPU/CPU, and VRAM. Add K1 rules (0 parameters) and BM25 as the floor. The question becomes "where does the LLM start beating rules?" That point is the answer for on-device dev agents. Contrast it with 2610.05099, where untrained small models are weak as *multi-turn agents*, and test whether a single-shot role rescues them.
2. **Held-out, uncontaminated evaluation.** Gemma's training data may contain SWE-bench issues: "SWE-Bench Illusion" (arXiv:2506.12286, NeurIPS 2025) shows models naming the buggy file from issue text alone at up to 76%, falling to 53% off-benchmark [V snippet]. Do three things. (a) Freeze rules and prompt, then evaluate on SWE-bench Lite or Verified across all 12 repos, or at least the competition's httpx/fastapi. (b) Add post-cutoff issues: GitHub issues closed after Gemma 4's release, or SWE-rebench / SWE-bench-Live style data [U]. (c) Run a **memorization probe**: ask Gemma for the file path with *no* repo file list and *no* grep, as in the Illusion paper. If that alone reaches 70%, the grep pipeline's value is in doubt.
3. **Cost-normalized comparison with published systems.** Report Hit@1 on SWE-bench Lite next to the published numbers for Agentless (0.697), SWE-agent (0.573), LocAgent (0.759) and Caumartin & Melo (0.727), all from arXiv:2512.07022 [V]. Report input/output tokens per issue and lines read. If 12B single-shot gets within ~10 points of these at about 1/50 of the tokens, that is the paper. Optional: end-to-end resolution on a small subset, with Gemma 12B as the editor using K2 windows versus BM25 files, to show that localization quality carries through.
4. A cheap add-on: **the same keywords through BM25 versus through the grep scorer.** This separates "better query" (Caumartin & Melo's claim) from "better scorer and windows" (the pilot's own contribution).

### Honest weaknesses to state
- n = 55, two tiny repos (about 17 searchable files; random Hit@5 is 35%). One issue is 1.8 points. 80% vs. 69% is 6 issues, so report a paired test (McNemar) or bootstrap CI.
- The rules and the two K2 parser fixes were developed on the same 55 issues. There is no held-out set.
- Contamination: requests and flask are in SWE-bench and are heavily scraped. See the memorization probe above.
- Only one prompt and one run per issue. Report variance across seeds/temperatures.
- File level only. Most 2025–26 papers report function level too.
- Merging K1 and K2 *hurts* (73%), which complicates a "rules plus LLM" story.

### Sources (primary unless noted)
arXiv:2310.06770; 2405.15793; 2404.05427; 2407.01489; 2502.00350 (+ github.com/fishmingyu/orcaloca); 2503.22424; 2503.09089 (+ github.com/gersteinlab/LocAgent); 2502.15292; 2505.07849 (ICLR 2026: https://iclr.cc/virtual/2026/poster/10009753); 2512.20482; 2410.14684; 2512.07022; 2607.11046; 2610.05099; 2603.17829; 2606.11976; 2606.24820; 2506.12728; 2506.07636; 2504.21798; 2506.12286; 2501.10542; 2510.04468; 1808.00594; 2108.09646; 2401.04514 (ACL 2024: https://aclanthology.org/2024.acl-long.75); 2212.10496; 2308.05487; 2409.13642; 2509.20552; 2605.13491; 2501.18005; SWE-Fixer https://aclanthology.org/2025.findings-acl.62.pdf; Moatless https://github.com/aorwall/moatless-tools; BLUiR https://ischool.utexas.edu/ml/papers/saha-ase13.pdf; Locus https://cse.hkust.edu.hk/faculty/scc/publ/ase16-Locus-preprint.pdf; Chaparro ICSME 2017 https://par.nsf.gov/servlets/purl/10120539; Gemma releases https://ai.google.dev/gemma/docs/releases (secondary snippet).
