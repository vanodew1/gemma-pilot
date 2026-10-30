# Keyword-search pilot

A small-scale test of step (A) from the proposal: *search the repo with keywords from the issue, then open only the matching files and lines.*

**Question:** given only an issue's text, how often does keyword search rank the file the real fix changed near the top? This is called fault localization. It needs no model, no Docker and no test runs, and it is exactly what the agent's search tool would hand to Gemma.

## Data

Real GitHub issues from SWE-bench (`princeton-nlp/SWE-bench`, test split). There are 44 from `psf/requests` (one of the competition's dev-set repos) and 11 from `pallets/flask`, 55 in total. For each issue:
- the repo is read **at the commit before the fix** (`base_commit`), straight from git;
- the **gold files** are the files the real fix (`patch`) changed;
- searchable files are Python source only, excluding tests, docs and vendored libraries. That is 16 to 23 files per issue.

## Method (`pilot.py`)

1. **Extract keywords** from the issue text with fixed rules, each tagged by where it came from:

   | Kind | Weight | Examples | Rule |
   |---|---|---|---|
   | `path` | 5 | `requests/sessions.py` | `.py` paths, including traceback `File "..."` lines |
   | `ident` | 3 | `builtin_str`, `InvalidURL`, `send` | snake_case, CamelCase, dotted names, `backticked` code, traceback function names, exception names |
   | `error` | 3 | `Failed to parse the redirect location` | quoted prose and exception messages |
   | `word` | 1 | `redirect`, `binary` | other English words with 4 or more letters, minus stopwords |

2. **Search:** whole-word match of each keyword in every file, the same as `rg -w -F`. A `path` keyword matches by filename.
3. **Rank:** each file's score is the sum over keywords of `weight × (log(1 + hits) + def_bonus) × idf`.
   - `idf = log(1 + N / files containing the keyword)`, so words found everywhere count for little.
   - `def_bonus = 2` when the file contains `def <kw>` or `class <kw>`, so the file that *defines* the function beats big files that only call it.
4. **Open:** ±10-line windows around the strongest hits, at most 5 per file. This is what the model reads.

## Results (`results/results.md`)

55 issues. Hit@k = at least one gold file is in the top k.

| Method | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Mean lines opened (top 5) |
|---|---|---|---|---|---|
| B0 random | 9% | 24% | 35% | 27% | 1,225 |
| B1 BM25 (whole files) | 58% | 91% | 95% | 89% | 2,999 |
| K0 keyword search, no def bonus | 65% | 91% | 98% | 93% | 1,082 |
| **K1 keyword search** | **69%** | 91% | 98% | 93% | **1,079** |
| K1 + retry clues | 69% | **96%** | 98% | 94% | 1,402 |

- **B1, BM25** is the retrieval baseline from the SWE-bench paper (Jimenez et al., 2024). It treats the issue as a bag of words and the agent reads whole files.
- **K1 + retry clues** stands in for loop (B). It adds the failing test's code to the query, which is what the agent would see after a failed test run.

**Reading it:**
- Keyword search puts the right file **first** 69% of the time, against 58% for BM25. The model reads about **⅓ as many lines** (1,079 vs 2,999), because it opens windows instead of whole files.
- The definition bonus is worth +4 points at Hit@1.
- Retry clues push Hit@3 from 91% to 96%. This is early evidence for the proposal's claim that searching again with error text helps.

**Caveats to state honestly:**
- These repos are small (about 17 files), so top 5 is easy even by chance: random gets 35%. **Hit@1 is the number that matters.**
- 55 issues is small. One issue is about 1.8 points.
- The rules were tuned by looking at these same issues; there is no held-out set yet. The next step is to freeze the rules and test on new issues from httpx or fastapi.

## Failure analysis

K1 misses Hit@1 on 17 of 55 issues. The main patterns:

1. **Hub files win.** Large central files mention almost every concept, so they collect hits on every keyword.
   - In all 4 flask misses, `src/flask/app.py` ranks first, ahead of `blueprints.py` or `cli.py`.
   - In 6 requests misses, `requests/models.py` ranks first.
   - The definition bonus fixed 2 such cases but not these.
2. **The issue describes only a symptom.** `psf__requests-6028` ("Proxy authentication bug") reports an HTTP 407 on Python 3.8.12. The fix is in `utils.py`, and nothing in the issue points there. Finding it needs reasoning about the cause, which is where the model comes in.
3. **The fix adds code that doesn't exist yet.** In `psf__requests-4356` (a misleading exception for a malformed `https_proxy`), the fix adds a new `InvalidProxyURL` class to `exceptions.py`. A search of the code before the fix can't match a class that hasn't been written.

Run `python run.py --trace <id>` on any of these to show why it missed.

## Demo script (Monday)

```powershell
cd "D:\AI Project\pilot"
.venv\Scripts\activate
python run.py --trace psf__requests-2317   # 1. one issue end to end (a win)
python run.py --trace pallets__flask-4045  # 2. a miss: hub file app.py beats blueprints.py
type results\results.md                   # 3. the results table
python -m pytest -q                        # 4. unit tests for the method
```

The trace prints five steps:
1. the issue;
2. the extracted keywords, colour-coded by kind;
3. the hits for each keyword;
4. the ranked files, with the gold file marked;
5. the exact lines the model would read.

**How it plugs into the agent:** `extract_keywords` + `rank_files` + the windows become the agent's `search` tool. On a failed test, the error output is appended to the query and the search runs again. That is loop (B).

## Next steps

- **K2:** ask local Gemma 4 12B (via Ollama) for extra keywords and merge them with K1. This needs `ollama pull gemma4:12b`.
- Reduce hub-file bias, for example by normalising by file length or preferring definitions more strongly.
- Run on a held-out set: issues from httpx and fastapi, the other competition dev-set repos.

## Reproduce

```powershell
python -m venv .venv; .venv\Scripts\pip install datasets rank_bm25 "pytest==8.3.5"
git clone https://github.com/psf/requests repos/requests
git clone https://github.com/pallets/flask repos/flask
# data/instances.jsonl: SWE-bench test split filtered to psf/requests + pallets/flask
python run.py
```
