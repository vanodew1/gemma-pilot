"""Gate replay: run v6's deterministic checks on saved patches, with no model.

For every unique saved agent patch (and every reference patch) on the tasks
that grade at home, apply it in a fresh sandbox and compute the gate's verdict:

    EMPTY           no source file changed
    BROKEN          see below
    OK              everything else (ordinary assertion failures are ignored)

BROKEN means a changed .py file does not compile, or the nearest test file
shows a new loading error whose traceback names a file the edit changed.

Pass mark: no resolved patch and no reference patch is flagged EMPTY or BROKEN. The unresolved patches the gate flags are what v6 can rescue.

    python gate_replay.py --gold-results ../../bench_runs/<gold run>/results.json
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import hashlib
import importlib.util
import json
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location("local_bench", Path(__file__).with_name("local_bench.py"))
lb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lb)

STATE = ('git add -N . ; git diff --stat | tail -1; F=$(git diff --name-only | grep "[.]py$"); '
         'if [ -z "$(git diff --name-only)" ]; then echo NO_CHANGES; elif [ -z "$F" ]; then echo COMPILE_OK; '
         'else python -m py_compile $F && echo COMPILE_OK; fi')
LOAD_ERROR = re.compile(r"SyntaxError|IndentationError|ImportError|ModuleNotFoundError|NameError"
                        r"|errors? during collection")
def testrun(box, paths: list[str]) -> str:
    quoted = " ".join(f"'{p}'" for p in paths)
    return box.sh(f"timeout 60 python -m pytest {quoted} -q --tb=short 2>&1 | tail -25", timeout=90)[1]


def verdict(task: dict, patch: str) -> dict:
    with lb.Box(task) as box:
        box.prepare("baseline")
        tests = [p for p in lb.changed_files(task["test_patch"]) if p.endswith(".py")]
        tests = [p for p in tests if box.sh(f"test -f '{p}'")[0] == 0]
        before = testrun(box, tests) if tests else ""
        if patch.strip():
            box.sh("cat > /tmp/agent.patch", stdin=(patch.rstrip("\n") + "\n").encode("utf-8"))
            if not lb.apply_patch(box, "/tmp/agent.patch"):
                return {"verdict": "NO_APPLY"}
        _, out, err = box.sh(STATE, timeout=60)
        state = out + err
        after = testrun(box, tests) if tests else ""
        changed = box.sh("git diff --name-only")[1].split()
        after_full = box.sh("timeout 60 python -m pytest " + " ".join(f"'{p}'" for p in tests)
                            + " -q --tb=long 2>&1 | grep -E 'File|^[a-zA-Z_/]+[.]py:[0-9]+'", timeout=90)[1] if tests else ""
    first = state.strip().split("\n")[0] if state.strip() else ""
    if "changed" not in first or "NO_CHANGES" in state:
        v = "EMPTY"
    elif "COMPILE_OK" not in state:
        v = "BROKEN"
    elif (set(LOAD_ERROR.findall(after)) - set(LOAD_ERROR.findall(before))
          and any(path in after_full for path in changed)):
        v = "BROKEN"  # a loading error whose traceback names a file the edit changed
    else:
        v = "OK"
    return {"verdict": v, "state": state[-600:], "after_tail": after[-400:]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-results", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0, help="only the first N patches, for a smoke test")
    parser.add_argument("--only", nargs="*", default=[], help="only the correct fixes of these tasks")
    args = parser.parse_args()

    gradable = {r["instance_id"] for r in json.load(open(args.gold_results, encoding="utf-8"))["tasks"]
                if r.get("resolved")}
    tasks = {t["instance_id"]: t for t in lb.load_tasks() if t["instance_id"] in gradable}

    items, seen = [], set()
    for tid, task in tasks.items():
        items.append({"instance_id": tid, "source": "reference", "resolved": True, "patch": task["patch"]})
    for results in sorted(lb.OUT.glob("*agent_v*/results.json")):
        run = results.parent
        for row in json.load(open(results, encoding="utf-8"))["tasks"]:
            tid = row["instance_id"]
            path = run / "patches" / f"{tid}.patch"
            if tid not in tasks or not path.exists():
                continue
            patch = lb.strip_protected(path.read_bytes().decode("utf-8", "replace"))
            key = (tid, hashlib.md5(patch.encode()).hexdigest())
            if key in seen:
                continue
            seen.add(key)
            items.append({"instance_id": tid, "source": run.name, "resolved": bool(row.get("resolved")),
                          "patch": patch})
    print(f"{len(items)} unique patches on {len(tasks)} gradable tasks", flush=True)
    if args.only:
        items = [i for i in items if i["instance_id"] in args.only and i["resolved"]]
    if args.limit:
        items = items[-args.limit:] + items[:1]

    def one(item):
        try:
            return {**item, **verdict(tasks[item["instance_id"]], item["patch"])}
        except Exception as exc:  # one broken sandbox must not end the run
            return {**item, "verdict": "ERROR", "error": f"{type(exc).__name__}: {exc}"}

    rows = []
    with cf.ThreadPoolExecutor(args.workers) as pool:
        for row in pool.map(one, items):
            row.pop("patch")
            rows.append(row)
            print(row["instance_id"], row["source"][:40], "resolved" if row["resolved"] else "-", row["verdict"],
                  flush=True)

    table = collections.Counter((r["source"] == "reference", r["resolved"], r["verdict"]) for r in rows)
    false_alarms = [r for r in rows if r["resolved"] and r["verdict"] not in ("OK", "NO_APPLY", "ERROR")]
    out = lb.OUT / "gate_replay.json"
    out.write_text(json.dumps({"table": {str(k): v for k, v in table.items()}, "rows": rows}, indent=1),
                   encoding="utf-8")
    print("\n(reference?, resolved?, verdict): count")
    for key, count in sorted(table.items(), key=str):
        print(key, count)
    print(f"\nFalse alarms on correct fixes: {len(false_alarms)}"
          f" {[(r['instance_id'], r['source'][:30], r['verdict']) for r in false_alarms]}")
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
