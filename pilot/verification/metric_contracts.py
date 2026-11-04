"""Contracts on the code that turns model output into paper numbers.

Checked by CrossHair (symbolic execution over every input up to its search bound):
    python -m crosshair check --analysis_kind=asserts --per_condition_timeout=20 verification/metric_contracts.py

Each function's leading asserts are preconditions; the asserts after the call are the property.
"""
from typing import List

from experiments import named_first, parse_order
from pilot import Keyword, hit_at_k, recall_at_k


def parse_order_is_a_permutation(reply: str, n: int) -> None:
    """Whatever Gemma replies, the selector reorders the candidates: none lost, none invented."""
    assert 1 <= n <= 6
    order = parse_order(reply, n)
    assert sorted(order) == list(range(n))


def named_first_is_a_permutation(ranked: List[str], terms: List[str]) -> None:
    """The no-call rerank only reorders the keyword ranking; Hit@k can't gain a file from nowhere."""
    assert len(set(ranked)) == len(ranked) <= 5
    assert len(terms) <= 3
    out = named_first(ranked, [Keyword(t, "path") for t in terms])
    assert sorted(out) == sorted(ranked)


def hit_at_k_matches_definition(ranked: List[str], gold: List[str], k: int) -> None:
    """Hit@k is true exactly when some gold file sits in the top k, and never drops as k grows."""
    assert 0 <= k <= 6 and len(ranked) <= 6 and len(gold) <= 3
    got = hit_at_k(ranked, set(gold), k)
    assert got == any(p in set(gold) for p in ranked[:k])
    assert (not got) or hit_at_k(ranked, set(gold), k + 1)


def recall_is_a_fraction(ranked: List[str], gold: List[str], k: int) -> None:
    """Recall@k stays in [0, 1] and is 1 only when every gold file is in the top k."""
    assert 0 <= k <= 6 and len(ranked) <= 6 and 1 <= len(set(gold)) <= 3
    r = recall_at_k(ranked, set(gold), k)
    assert 0.0 <= r <= 1.0
    assert (r == 1.0) == set(gold).issubset(ranked[:k])
