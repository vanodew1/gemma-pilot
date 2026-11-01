"""Idea tests on the pilot issues (code check only, not paper data).

S1 select-from-rules: the K1 rules search proposes its top 5 files; Gemma sees the issue and
   a short outline of each file (class and def names) and orders the 5 candidates.
S2 select-from-own: same, but the candidates are Gemma's own K2 keyword top 5.
P  memory probe: Gemma names the file to change from the issue alone (no file list, no search).

Usage:
    python experiments.py gemma4:12b gemma4:e4b gemma4:e2b
Replies are cached in data/exp_<model>.json.
"""
import json
import re
import sys
import urllib.request

from pilot import extract_keywords, gold_files, rank_files
from run import (REPOS, ROOT, files_at, gemma_cache_path, gemma_reply, load_instances,
                 parse_llm_keywords, size_label)

K = 5
OUTLINE = re.compile(r"^(\s*)(?:async\s+)?(def|class)\s+(\w+)", re.M)

SELECT_PROMPT = """You are helping fix a bug in a Python repository. Below is the bug report and
{k} candidate source files, each with an outline of the classes and functions it defines.
Order the candidates from most to least likely to contain the code that must change.
Reply with only a JSON list of the candidate numbers, for example [2, 1, 3, 5, 4].

BUG REPORT:
{issue}

CANDIDATES:
{candidates}"""

PROBE_PROMPT = """This bug report is from the GitHub repository {repo}. Which source file in that
repository must change to fix it? Reply with only the file path, for example src/pkg/module.py.

BUG REPORT:
{issue}"""


def outline(text, max_names=40):
    """Class names, top-level functions and methods (indented under a class), in file order."""
    names = []
    for indent, kind, name in OUTLINE.findall(text):
        names.append(("  " if indent else "") + f"{kind} {name}")
    if len(names) > max_names:
        names = names[:max_names] + [f"... {len(names) - max_names} more"]
    return "\n".join(names) or "(no classes or functions)"


def ask(model, prompt):
    body = json.dumps({"model": model, "stream": False, "think": False,
                       "options": {"temperature": 0, "num_ctx": 8192},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        out = json.load(resp)
    return {"reply": out["message"]["content"], "seconds": round(out["total_duration"] / 1e9, 2)}


def cached(cache, key, model, prompt):
    if key not in cache:
        cache[key] = ask(model, prompt)
    return cache[key]


def answer_list(reply):
    """Text of the last [...] in the reply: the final answer, not a "[1]" quoted in the reasoning."""
    lists = re.findall(r"\[([^\[\]]*)\]", reply)
    return lists[-1] if lists else None


def parse_order(reply, n):
    """Candidate order from the reply's last list of 1-based numbers; candidates it leaves out keep
    their original place after the parsed ones (all of them, if there's no list)."""
    picked = []
    for tok in re.findall(r"\d+", answer_list(reply) or ""):
        i = int(tok) - 1
        if 0 <= i < n and i not in picked:
            picked.append(i)
    return picked + [i for i in range(n) if i not in picked]


def named_first(ranked, keywords):
    """No-call baseline: files whose path the model wrote itself move to the front, rank kept."""
    paths = [k.term for k in keywords if k.kind == "path"]
    named = [p for p in ranked if any(p == t or p.endswith("/" + t) for t in paths)]
    return named + [p for p in ranked if p not in named]


def select(model, cache, key, issue, files, candidates):
    blocks = [f"[{i + 1}] {p}\n{outline(files[p])}" for i, p in enumerate(candidates)]
    prompt = SELECT_PROMPT.format(k=len(candidates), issue=issue[:6000], candidates="\n\n".join(blocks))
    call = cached(cache, key, model, prompt)
    return [candidates[i] for i in parse_order(call["reply"], len(candidates))], call


def probe_hit(reply, gold):
    paths = {m.strip("`'\" ").replace("\\", "/") for m in re.findall(r"[\w./\\-]+\.py", reply)}
    return any(g == p or g.endswith("/" + p) or p.endswith("/" + g) for p in paths for g in gold)


def main(models):
    instances = load_instances()
    table = {}
    for model in models:
        cpath = ROOT / f"data/exp_{model.replace(':', '-')}.json"
        cache = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else {}
        kcache_path = gemma_cache_path(model)
        kcache = json.loads(kcache_path.read_text(encoding="utf-8")) if kcache_path.exists() else {}
        stats = {"n": 0, "K1@1": 0, "K2@1": 0, "N@1": 0, "S1@1": 0, "S1@3": 0, "S2@1": 0, "S2@3": 0,
                 "P": 0, "S1 gold in pool": 0, "S2 gold in pool": 0, "secs": 0.0, "unparsed": 0}
        for inst in instances:
            files = files_at(REPOS[inst["repo"]], inst["base_commit"])
            gold = gold_files(inst["patch"]) & set(files)
            if not gold:
                continue
            iid, issue = inst["instance_id"], inst["problem_statement"]
            k1 = [p for p, _ in rank_files(extract_keywords(issue), files)][:K]
            k2_kws = parse_llm_keywords(gemma_reply(inst, files, model, kcache)["reply"])
            k2_all = [p for p, _ in rank_files(k2_kws, files)]
            k2 = k2_all[:K]
            nf = named_first(k2_all, k2_kws)
            s1, c1 = select(model, cache, iid + ":S1", issue, files, k1) if k1 else ([], {"seconds": 0})
            s2, c2 = select(model, cache, iid + ":S2", issue, files, k2) if k2 else ([], {"seconds": 0})
            pr = cached(cache, iid + ":P", model, PROBE_PROMPT.format(repo=inst["repo"], issue=issue[:6000]))
            cpath.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            hit = lambda ranked, k: bool(set(ranked[:k]) & gold)
            stats["n"] += 1
            stats["K1@1"] += hit(k1, 1)
            stats["K2@1"] += hit(k2, 1)
            stats["N@1"] += hit(nf, 1)
            stats["S1@1"] += hit(s1, 1)
            stats["S1@3"] += hit(s1, 3)
            stats["S2@1"] += hit(s2, 1)
            stats["S2@3"] += hit(s2, 3)
            stats["S1 gold in pool"] += hit(k1, K)
            stats["S2 gold in pool"] += hit(k2, K)
            stats["P"] += probe_hit(pr["reply"], gold)
            stats["secs"] += c1["seconds"] + c2["seconds"]
            stats["unparsed"] += sum(not re.search(r"\d", answer_list(c.get("reply", "")) or "")
                                     for c in (c1, c2) if "reply" in c)
        table[size_label(model)] = stats
        print(size_label(model), stats, flush=True)

    cols = ["K1@1", "S1@1", "S1@3", "S1 gold in pool", "K2@1", "N@1", "S2@1", "S2@3", "S2 gold in pool", "P"]
    lines = ["| Model | " + " | ".join(cols) + " | unparsed picks | mean s per pick |", "|---" * (len(cols) + 3) + "|"]
    for m, s in table.items():
        n = s["n"]
        lines.append(f"| {m} | " + " | ".join(f"{s[c] / n:.0%}" for c in cols)
                     + f" | {s['unparsed']}/{2 * n} | {s['secs'] / (2 * n):.1f} |")
    out = "\n".join(lines)
    n = next(iter(table.values()))["n"]
    (ROOT / "results/experiments.md").write_text(
        f"# Selector and memory-probe check ({n} pilot issues; code check only)\n\n"
        "Gold in pool = a gold file is among the 5 candidates, the ceiling for S1/S2.\n\n"
        "K1/K2 = keyword ranking alone. N = K2 with files the model named itself moved first (no extra call). S1/S2 = Gemma orders the top 5 of K1/K2 from file outlines. "
        "P = file named from the issue alone.\n\n" + out + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:] or ["gemma4:12b"])
