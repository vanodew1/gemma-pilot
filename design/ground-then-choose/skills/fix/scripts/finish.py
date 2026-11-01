"""Skill script: produce the diff to submit, with test-file edits dropped.

Encodes the TLA+ rule NoTestEditsSubmitted (verification/pipeline/Pipeline.tla) in code,
not in the prompt. Prints the diff, or NO_PATCH when nothing non-test changed.
Uses ground.is_source's test rules so "what locate searches" and "what finish keeps"
cannot drift apart.
"""
from __future__ import annotations

from pathlib import Path


def submittable_diff(repo: Path) -> str:
    """`git diff` restricted to changed paths that are not tests (ground.is_test_path), or "NO_PATCH"."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError
