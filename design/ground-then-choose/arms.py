"""Every experimental arm, declared exactly once.

Each arm is one decorated function `(view, model) -> Outcome`. The decorator appends it
to METHODS in definition order; table columns, CSV rows, CLI choices and comparisons all
derive from METHODS. Adding an arm = writing one function. There is no second list.

An arm's identity is (Method, Model | None), never a string to parse back
(fixes "method names parsed back as data").
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable

import ground
from ground import Files, Keyword, Menu, Ranking
from oracle import Model, Oracle


@dataclass(frozen=True)
class Task:
    """Parsed once at the corpus boundary (experiment.load_tasks); trusted inside."""
    instance_id: str
    repo: str
    problem_statement: str
    gold: frozenset[str]  # gold_files(patch) & set(files); tasks with empty gold are dropped at load
    files: Files


@dataclass(frozen=True)
class Call:
    kind: str
    seconds: float | None
    out_tokens: int | None
    parsed_ok: bool


@dataclass(frozen=True)
class Outcome:
    """What an arm produced for one task. Hit@k / recall / McNemar all read `ranking`.
    `pool` is set for choose-from-menu arms: the ceiling (gold in pool)."""
    ranking: Ranking
    pool: Ranking | None = None
    calls: tuple[Call, ...] = ()


class View:
    """Per-task memo shared by all arms of one task, so S2 reuses K2's keyword call and
    N reuses it too, without a second cache key. One View per (task, oracle); not shared
    across tasks, never written by two arms concurrently (the runner is sequential)."""

    def __init__(self, task: Task, oracle: Oracle) -> None:
        self.task, self.oracle = task, oracle
        self._k2: dict[str, tuple[list[Keyword], Call]] = {}

    @cached_property
    def k1(self) -> Ranking:
        return ground.keyword_ranking(ground.extract_keywords(self.task.problem_statement), self.task.files)

    def k2(self, model: Model) -> tuple[list[Keyword], Ranking, Call]:
        """Model keywords (one cached Oracle call) and their ranking."""
        raise NotImplementedError

    def choose(self, model: Model, menu: Menu) -> Outcome:
        """Ask choice_question(issue, menu); ranking = menu.order(parsed), pool = menu.pool.
        Empty menu -> Outcome((), pool=()) with no call (matches experiments.py)."""
        raise NotImplementedError


@dataclass(frozen=True)
class Method:
    code: str          # "S1": short id, CSV `method` column, CLI selector
    label: str         # "pick from rules' top 5": table header text
    needs_model: bool
    rank: Callable[[View, Model | None], Outcome] = field(repr=False, compare=False)


METHODS: list[Method] = []


def method(code: str, label: str, *, model: bool = False) -> Callable[[Callable], Method]:
    """Register `fn` as an arm and bind its module name to the Method (so `S1` below IS the
    Method object comparisons refer to). Duplicate codes raise at import."""
    raise NotImplementedError


@dataclass(frozen=True)
class Arm:
    method: Method
    model: Model | None  # None iff not method.needs_model

    @property
    def label(self) -> str:
        return f"{self.method.code} {self.method.label}" + (f" ({self.model.label})" if self.model else "")


def arms_for(models: list[Model], codes: list[str] | None = None) -> list[Arm]:
    """Cartesian expansion of METHODS x models (model-free methods once), optionally filtered."""
    raise NotImplementedError


# --------------------------------------------------------------------------- the arms
@method("B0", "random")
def B0(v: View, _: None) -> Outcome:
    paths = sorted(v.task.files)
    return Outcome(tuple(random.Random(v.task.instance_id).sample(paths, len(paths))))


@method("B1", "BM25 whole files")
def B1(v: View, _: None) -> Outcome:
    """rank_bm25 lives here, not in ground: the agent never uses BM25."""
    raise NotImplementedError


@method("K1", "rules keywords")
def K1(v: View, _: None) -> Outcome:
    return Outcome(v.k1)


@method("K2", "model keywords", model=True)
def K2(v: View, m: Model) -> Outcome:
    _, ranking, call = v.k2(m)
    return Outcome(ranking, calls=(call,))


@method("N", "named-first over K2", model=True)
def N(v: View, m: Model) -> Outcome:
    kws, ranking, call = v.k2(m)
    return Outcome(tuple(ground.named_first(ranking, kws)), calls=(call,))


@method("S1", "pick from K1 top 5", model=True)
def S1(v: View, m: Model) -> Outcome:
    """The agent, measured. ground.locate is the same call locate.py makes."""
    return v.choose(m, ground.locate(v.task.problem_statement, v.task.files))


@method("S2", "pick from K2 top 5", model=True)
def S2(v: View, m: Model) -> Outcome:
    _, ranking, call = v.k2(m)
    out = v.choose(m, ground.build_menu(ranking, v.task.files))
    return Outcome(out.ranking, out.pool, (call, *out.calls))


@method("P", "memory probe", model=True)
def P(v: View, m: Model) -> Outcome:
    """Paths named from the issue alone, resolved onto repo files."""
    raise NotImplementedError


@method("S1v", "S1 Borda over 3 menu rotations", model=True)
def S1v(v: View, m: Model) -> Outcome:
    """Position-bias control: choose over build_menu(k1, rotate=r) for r in 0..2, borda.
    Rotation 0 is the S1 call, so it is a cache hit; 2 extra calls per task."""
    raise NotImplementedError


@method("V", "Borda of K1, S1, S2", model=True)
def V(v: View, m: Model) -> Outcome:
    """Cross-arm vote. Reuses the memoized S1/S2 calls (cache hits), no new prompts."""
    raise NotImplementedError


# Paired McNemar on Hit@1, expanded per model; a model-free side pairs with every model.
# Referencing Method objects means a renamed or deleted arm is an ImportError/NameError,
# not a silently missing row.
COMPARISONS: tuple[tuple[Method, Method], ...] = (
    (S1, K1), (S1, K2), (S2, K2), (S1, N), (S1, S2), (S1v, S1), (V, S1),
)
