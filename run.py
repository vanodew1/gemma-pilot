"""Run the keyword-search pilot over SWE-bench instances and write results.

Usage:
    python run.py                 # all instances in data/instances.jsonl
    python run.py --trace psf__requests-2317   # one issue, end to end
    python run.py --gemma         # also K2: Gemma 4 12B (Ollama) suggests keywords
"""
import argparse
import csv
import json
import random
import re
import subprocess
import urllib.request
from pathlib import Path

from rank_bm25 import BM25Okapi

from pilot import (count_hits, extract_keywords, gold_files, hit_at_k, parse_llm_keywords,
                   rank_files, recall_at_k)

ROOT = Path(__file__).parent
REPOS = {"psf/requests": ROOT / "repos/requests", "pallets/flask": ROOT / "repos/flask"}
KS = (1, 3, 5)
WINDOW = 10  # lines of context either side of a hit, as the agent would open
GEMMA = "gemma4:12b"
GEMMA_CACHE = ROOT / "data/gemma_keywords.json"
GEMMA_PROMPT = """You are helping fix a bug in a Python repository. Below are the bug report and the
repository's source files. List the strings to grep the repository for to find the code that
must change: function, class and variable names, file paths from the list, and exact error
message text. Include names you expect in the faulty code even if the report doesn't say them.
Reply with only a JSON list of at most 15 strings.

SOURCE FILES:
{files}

BUG REPORT:
{issue}"""


def gemma_keywords(inst, files, cache):
    """Gemma's suggested keywords for one issue, cached by instance_id (raw reply kept)."""
    iid = inst["instance_id"]
    if iid not in cache:
        prompt = GEMMA_PROMPT.format(files="\n".join(sorted(files)), issue=inst["problem_statement"][:6000])
        body = json.dumps({"model": GEMMA, "stream": False, "think": False,
                           "options": {"temperature": 0, "num_ctx": 8192},
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request("http://localhost:11434/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            cache[iid] = json.load(resp)["message"]["content"]
        GEMMA_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return parse_llm_keywords(cache[iid])


def is_source(path):
    """Searchable files: Python source, no tests, docs, examples or vendored libraries.

    Vendored = anything below `packages/<lib>/` (old requests bundled urllib3 and
    chardet there); `requests/packages/__init__.py` itself stays searchable.
    """
    parts = path.split("/")
    name = parts[-1]
    if "packages" in parts[:-2]:
        return False
    return (
        name.endswith(".py")
        and not name.startswith("test_")
        and not name.endswith("_test.py")
        and name != "conftest.py"
        and not {"tests", "test", "testing", "docs", "examples"} & set(parts[:-1])
    )


def files_at(repo, commit):
    """{path: text} for every source file at `commit`, read straight from git."""
    names = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    names = [n for n in names if is_source(n)]
    batch = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch"],
        input="".join(f"{commit}:{n}\n" for n in names).encode(),
        capture_output=True, check=True,
    ).stdout
    files, pos = {}, 0
    for name in names:
        header_end = batch.index(b"\n", pos)
        size = int(batch[pos:header_end].split()[2])
        start = header_end + 1
        files[name] = batch[start:start + size].decode("utf-8", "replace")
        pos = start + size + 1
    return files


def added_lines(diff):
    return "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))


def windows(keywords, text, radius=WINDOW, max_spans=5):
    """Merged (start, end) line ranges around strong keyword hits in `text`.

    Plain words only rank files; they don't open windows unless nothing stronger hit.
    Keeps the `max_spans` spans with the most hits.
    """
    lines = text.splitlines()
    strong = [k for k in keywords if k.kind != "word"]
    hit_terms = count_hits(strong, {"f": text}) or count_hits(keywords, {"f": text})
    hit_lines = set()
    for term in hit_terms:
        pat = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)") if " " not in term else re.compile(re.escape(term))
        hit_lines |= {i for i, line in enumerate(lines) if pat.search(line)}
    spans = []
    for i in sorted(hit_lines):
        lo, hi = max(0, i - radius), min(len(lines), i + radius + 1)
        if spans and lo <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(spans[-1][1], hi))
        else:
            spans.append((lo, hi))
    densest = sorted(spans, key=lambda s: -sum(s[0] <= i < s[1] for i in hit_lines))
    return sorted(densest[:max_spans])


def lines_opened(ranked, files, keywords=None, k=5):
    """Context cost: lines the agent would read from the top-k files.

    Keyword methods open windows around hits; whole-file methods open everything.
    """
    total = 0
    for path in ranked[:k]:
        if keywords is None:
            total += files[path].count("\n") + 1
        else:
            total += sum(hi - lo for lo, hi in windows(keywords, files[path])) or WINDOW * 2
    return total


def tokenize(text):
    return [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]+", text)]


def run_methods(inst, files, gemma_cache=None):
    """{method: (ranked paths, lines opened)} for one instance."""
    paths = sorted(files)
    issue = inst["problem_statement"]
    rng = random.Random(inst["instance_id"])

    bm25 = BM25Okapi([tokenize(files[p]) for p in paths])
    scores = bm25.get_scores(tokenize(issue))
    b1 = [p for _, p in sorted(zip(scores, paths), key=lambda sp: -sp[0])]

    k1_kws = extract_keywords(issue)
    k0 = [p for p, _ in rank_files(k1_kws, files, define_bonus=0.0)]
    k1 = [p for p, _ in rank_files(k1_kws, files)]

    # Retry stand-in: the failing test's code is what a failed run would show the agent.
    r_kws = extract_keywords(issue + "\n" + added_lines(inst["test_patch"]))
    r = [p for p, _ in rank_files(r_kws, files)]

    b0 = rng.sample(paths, len(paths))
    methods = {
        "B0 random": (b0, lines_opened(b0, files)),
        "B1 BM25 (whole files)": (b1, lines_opened(b1, files)),
        "K0 keyword search, no def bonus": (k0, lines_opened(k0, files, k1_kws)),
        "K1 keyword search": (k1, lines_opened(k1, files, k1_kws)),
        "K1 + retry clues": (r, lines_opened(r, files, r_kws)),
    }
    if gemma_cache is not None:
        g_kws = gemma_keywords(inst, files, gemma_cache)
        g = [p for p, _ in rank_files(g_kws, files)]
        merged = list({k.term: k for k in g_kws + k1_kws}.values())  # Gemma's kind wins on overlap
        m = [p for p, _ in rank_files(merged, files)]
        methods["K2 Gemma keywords only"] = (g, lines_opened(g, files, g_kws))
        methods["K1 + K2 Gemma keywords"] = (m, lines_opened(m, files, merged))
    return methods


def load_instances():
    with open(ROOT / "data/instances.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def evaluate(use_gemma=False):
    gemma_cache = None
    if use_gemma:
        gemma_cache = json.loads(GEMMA_CACHE.read_text(encoding="utf-8")) if GEMMA_CACHE.exists() else {}
    rows = []
    for inst in load_instances():
        files = files_at(REPOS[inst["repo"]], inst["base_commit"])
        gold = gold_files(inst["patch"]) & set(files)
        if not gold:
            continue  # fix touched only non-source files
        for method, (ranked, cost) in run_methods(inst, files, gemma_cache).items():
            row = {"instance_id": inst["instance_id"], "method": method, "n_files": len(files),
                   "gold": " ".join(sorted(gold)), "top5": " ".join(ranked[:5]), "lines_opened": cost}
            for k in KS:
                row[f"hit@{k}"] = int(hit_at_k(ranked, gold, k))
            row["recall@5"] = round(recall_at_k(ranked, gold, 5), 3)
            rows.append(row)
        print(f"{inst['instance_id']}: {len(files)} files, gold={sorted(gold)}")
    return rows


def write_results(rows):
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with open(out / "per_instance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    methods = list(dict.fromkeys(r["method"] for r in rows))
    n = len({r["instance_id"] for r in rows})
    lines = [f"# Keyword-search pilot results\n",
             f"{n} SWE-bench issues (psf/requests, pallets/flask). Hit@k = a file the real fix touched is in the top k.\n",
             "| Method | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Mean lines opened (top 5) |",
             "|---|---|---|---|---|---|"]
    for m in methods:
        rs = [r for r in rows if r["method"] == m]
        mean = lambda key: sum(r[key] for r in rs) / len(rs)
        lines.append(f"| {m} | {mean('hit@1'):.0%} | {mean('hit@3'):.0%} | {mean('hit@5'):.0%} "
                     f"| {mean('recall@5'):.0%} | {mean('lines_opened'):,.0f} |")
    (out / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


COLORS = {"path": "\033[95m", "ident": "\033[96m", "error": "\033[93m", "word": "\033[37m"}
RESET, GREEN, RED, BOLD = "\033[0m", "\033[92m", "\033[91m", "\033[1m"


def trace(instance_id):
    inst = next(i for i in load_instances() if i["instance_id"] == instance_id)
    files = files_at(REPOS[inst["repo"]], inst["base_commit"])
    gold = gold_files(inst["patch"]) & set(files)

    print(f"{BOLD}1. ISSUE{RESET} {instance_id}\n{inst['problem_statement'].strip()[:1500]}\n")

    kws = extract_keywords(inst["problem_statement"])
    print(f"{BOLD}2. KEYWORDS{RESET} (" + ", ".join(f"{COLORS[k]}{k}{RESET}" for k in COLORS) + ")")
    print("   " + "  ".join(f"{COLORS[k.kind]}{k.term}{RESET}" for k in kws) + "\n")

    hits = count_hits(kws, files)
    print(f"{BOLD}3. SEARCH{RESET} over {len(files)} source files at {inst['base_commit'][:10]}")
    for k in kws:
        if k.term in hits:
            where = ", ".join(f"{p}({n})" for p, n in sorted(hits[k.term].items(), key=lambda x: -x[1])[:4])
            print(f"   {COLORS[k.kind]}{k.term}{RESET} -> {len(hits[k.term])} files: {where}")
    print()

    print(f"{BOLD}4. RANKED FILES{RESET} (gold = {sorted(gold)})")
    ranked = rank_files(kws, files)
    for i, (p, s) in enumerate(ranked[:5], 1):
        mark = f"{GREEN}<- GOLD{RESET}" if p in gold else ""
        print(f"   {i}. {p:40s} score={s:6.2f} {mark}")
    top = [p for p, _ in ranked]
    ok = hit_at_k(top, gold, 3)
    print(f"\n   Hit@3: {GREEN + 'YES' if ok else RED + 'NO'}{RESET}\n")

    if top:
        best = top[0]
        print(f"{BOLD}5. WHAT THE MODEL WOULD READ{RESET} from {best} (+/-{WINDOW} lines around hits)")
        src = files[best].splitlines()
        for lo, hi in windows(kws, files[best])[:2]:
            print(f"   --- lines {lo + 1}-{hi} ---")
            for n in range(lo, hi):
                print(f"   {n + 1:5d} | {src[n]}")
        print(f"\n   Lines opened from top 5: {lines_opened(top, files, kws)}"
              f"  vs whole files: {lines_opened(top, files)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", help="instance_id to trace end to end")
    ap.add_argument("--gemma", action="store_true", help="add K2 rows (needs `ollama serve` with gemma4:12b)")
    args = ap.parse_args()
    if args.trace:
        trace(args.trace)
    else:
        write_results(evaluate(args.gemma))
