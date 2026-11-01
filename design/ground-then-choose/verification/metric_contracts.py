"""Contracts on the code that turns model output into paper numbers.

Diff vs the repo version: the import block only. Every contract body is unchanged, and
three new contracts cover the new pure steps. Same CrossHair command.
"""
from typing import List

from ground import Keyword, borda, build_menu, hit_at_k, named_first, parse_order, recall_at_k

# parse_order_is_a_permutation, named_first_is_a_permutation,
# hit_at_k_matches_definition, recall_is_a_fraction: unchanged.


def menu_order_is_a_permutation_of_pool(paths: List[str], reply: str, rotate: int) -> None:
    """Whatever the model replies, S-arm rankings are a reordering of the menu's pool."""
    assert len(set(paths)) == len(paths) <= 6 and 0 <= rotate <= 4
    menu = build_menu(tuple(paths), {p: "" for p in paths}, rotate=rotate)
    out = menu.order(parse_order(reply, len(menu.candidates)))
    assert sorted(out) == sorted(menu.pool) == sorted(paths[:5])


def borda_is_a_permutation_of_the_union(a: List[str], b: List[str]) -> None:
    """Voting never invents or drops a file."""
    assert len(set(a)) == len(a) <= 4 and len(set(b)) == len(b) <= 4
    out = borda((tuple(a), tuple(b)))
    assert sorted(out) == sorted(set(a) | set(b))


def borda_of_one_is_identity(a: List[str]) -> None:
    assert len(set(a)) == len(a) <= 5
    assert borda((tuple(a),)) == tuple(a)
