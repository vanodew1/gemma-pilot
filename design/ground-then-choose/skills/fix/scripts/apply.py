"""Skill script: apply one search/replace edit to a file the agent chose.

Out of scope for localization; sketched only so the skill's script set is complete.
Exact-match replace; on no match or multiple matches, prints the nearest lines and exits 1
(the Editing -> Editing [tries left] edge of the pipeline statechart).
"""
from __future__ import annotations

from pathlib import Path


def apply_edit(path: Path, search: str, replace: str) -> str:
    raise NotImplementedError
