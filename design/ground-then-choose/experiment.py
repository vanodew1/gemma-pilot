"""Run arms over a corpus and report. Replaces run.py (evaluate, write_results) and
experiments.py (main) with one harness.

Usage:
    python experiment.py kaggle --models E2B E4B 12B --live     # fills the reply cache (needs `ollama serve`)
    python experiment.py kaggle --models E2B E4B 12B            # offline: cache only; CacheMiss if incomplete
    python experiment.py kaggle --arms K1 S1 --models E4B       # subset
    python experiment.py pilot  --models 12B                    # the 55 SWE-bench code-check issues
    python experiment.py kaggle --trace <instance_id>           # one task end to end (old run.py --trace)

Writes results/<corpus>/per_instance.csv (one row per task x arm, `method` and `model`
as separate columns) and results/<corpus>/results.md (Hit@1/3/5, recall@5, pool ceiling,
unparsed replies, seconds; then the McNemar table).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import ground
from arms import COMPARISONS, Arm, Outcome, Task, View, arms_for
from oracle import MODELS, Oracle

ROOT = Path(__file__).parent
KS = (1, 3, 5)


# --------------------------------------------------------------------------- corpus boundary
@dataclass(frozen=True)
class Corpus:
    """Where tasks and their repos live. Both corpora end in a directory checked out at
    base_commit, so ground.read_tree is the only file reader (same as the agent)."""
    name: str
    tasks_jsonl: Path
    repo_dir: Callable  # (raw task dict) -> Path of a working tree at base_commit; idempotent

CORPORA: dict[str, Corpus] = {}  # "kaggle": snapshots/<id>.tgz extracted once to data/kaggle/repos/<id>/
                                 # "pilot": `git worktree add` of repos/{requests,flask} at base_commit


def load_tasks(corpus: Corpus) -> Iterator[Task]:
    """Parse tasks.jsonl into Task (validation lives here and only here). Drops tasks whose
    gold files are all non-source, printing how many, so n is never hard-coded."""
    raise NotImplementedError


def extract_snapshot(tgz: Path, dest: Path) -> Path:
    """Idempotent: no-op if dest/.git exists; extracts to dest.tmp then renames (crash-safe)."""
    raise NotImplementedError


# --------------------------------------------------------------------------- run
@dataclass(frozen=True)
class Row:
    instance_id: str
    arm: Arm
    gold: frozenset[str]
    outcome: Outcome

    def hit(self, k: int) -> bool:
        return ground.hit_at_k(list(self.outcome.ranking), self.gold, k)


def run(tasks: Iterator[Task], arms: list[Arm], oracle: Oracle) -> list[Row]:
    """for task: view = View(task, oracle); for arm: arm.method.rank(view, arm.model).
    Sequential by design: one Oracle writer per cache file. Offline runs are pure replays."""
    raise NotImplementedError


# --------------------------------------------------------------------------- report
@dataclass(frozen=True)
class McNemar:
    gained: int  # a hit, b missed
    lost: int    # a missed, b hit
    p: float     # exact two-sided binomial on gained + lost


def mcnemar(a: list[bool], b: list[bool]) -> McNemar:
    raise NotImplementedError


def write_csv(rows: list[Row], path: Path) -> None:
    """Columns: instance_id, method, model, n_files, gold, top5, pool_hit, hit@1, hit@3,
    hit@5, recall@5, calls, unparsed, seconds, out_tokens."""
    raise NotImplementedError


def write_table(rows: list[Row], path: Path) -> str:
    """Arm table (rows in METHODS order, one per arm) + McNemar table from COMPARISONS
    expanded over the models present. Returns the markdown it wrote."""
    raise NotImplementedError


def trace(task: Task) -> None:
    """Human walkthrough: keywords, hits, K1 ranking, the menu text the agent would see."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
