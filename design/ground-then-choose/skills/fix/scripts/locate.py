"""Skill script: print the grounded top-5 candidates; the harness model chooses.

Runs offline in the Kaggle sandbox via the harness's `run_skill_script`. Stdlib + the
vendored ground.py (a byte copy of the repo's ground.py; never edit it here).

    python locate.py --issue-file ISSUE.md [--repo .]
        -> prints menu.render() then ground.CHOICE_INSTRUCTION, byte-identical to the
           CANDIDATES/instruction part of the S1 prompt the experiment measured.
    python locate.py --issue-file ISSUE.md --open 3
        -> prints candidate 3's path and ground.windows() around K1 hits (cheaper than
           read_file on the whole file). Recomputes the menu (pure, deterministic), so no
           state file; must run before any edit, which SKILL.md orders.

Never calls a model. Exit 0 with "NO_CANDIDATES" when K1 finds nothing, so the agent
falls back to the harness's search tools instead of erroring.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import ground  # vendored copy; see tests/test_vendor.py


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError


def show_menu(issue: str, repo: Path) -> str:
    """menu = ground.locate(issue, ground.read_tree(repo)); return render + instruction."""
    raise NotImplementedError


def show_candidate(issue: str, repo: Path, label: int) -> str:
    """1-based `label` into the same menu; out-of-range -> message listing valid labels."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
