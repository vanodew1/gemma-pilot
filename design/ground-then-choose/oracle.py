"""The one model client and the one reply cache (experiment side only; never vendored).

Replaces run.gemma_reply, run.gemma_cache_path, experiments.ask, experiments.cached.

    oracle = Oracle(cache_dir=ROOT / "data/replies", live=False)
    answer = oracle.ask(MODELS["E4B"], choice_question(issue, menu))
    answer.parsed.value, answer.parsed.ok, answer.seconds, answer.cached

Cache layout: one append-only JSONL file per model, data/replies/<model.label>.jsonl,
one line per reply: {"key": sha256(tag + "\\0" + prompt), "kind", "reply", "seconds",
"out_tokens"}. Keyed by content, so:
  * no hand-built keys like iid + ":S1" (the arm and the prompt cannot disagree);
  * rerunning, or crashing halfway and rerunning, converges (append-only, last line wins
    on load, idempotent per key);
  * one writer per file (one Oracle per process; models never share a file).
live=False (the default for reports) raises CacheMiss instead of calling Ollama, so
"reruns need no GPU" is a checked property, not a hope.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from ground import Parsed, Question

A = TypeVar("A")


@dataclass(frozen=True)
class Model:
    """A model under test. `label` is declared, never derived from `tag`
    (fixes size_label collisions across families)."""
    label: str  # "E4B": table column, cache filename, CSV `model` column
    tag: str    # "gemma4:e4b": what Ollama is asked for


# Declared once. Arms, cache files, and table rows all derive from this.
MODELS: dict[str, Model] = {m.label: m for m in (
    Model("E2B", "gemma4:e2b"),
    Model("E4B", "gemma4:e4b"),
    Model("12B", "gemma4:12b"),
)}


@dataclass(frozen=True)
class Answer(Generic[A]):
    parsed: Parsed[A]
    seconds: float | None
    out_tokens: int | None
    cached: bool


class CacheMiss(LookupError):
    """Raised in offline mode; message names model, question kind, and the prompt's first line."""


class Oracle:
    OLLAMA_URL = "http://localhost:11434/api/chat"
    OPTIONS = {"temperature": 0, "num_ctx": 8192}  # same as run.py / experiments.py

    def __init__(self, cache_dir: Path, live: bool = False) -> None:
        """Loads nothing eagerly; each model's JSONL is read on first use."""
        raise NotImplementedError

    def ask(self, model: Model, question: Question[A]) -> Answer[A]:
        """Cached reply if present, else (live only) one Ollama call, appended before returning.
        Parsing happens here, after the cache, so parser fixes apply to old replies for free
        (the parse_order bug of IDEAS-RUN section 6 would have needed no re-query)."""
        raise NotImplementedError

    def _call(self, model: Model, prompt: str) -> tuple[str, float, int | None]:
        """POST /api/chat with stream=False, think=False. Private: nothing else talks HTTP."""
        raise NotImplementedError


def import_legacy_caches(data_dir: Path, cache_dir: Path) -> int:
    """One-off: re-key data/gemma_keywords.json, keywords_*.json, exp_*.json (pilot, keyed by
    iid) into content-keyed JSONL by rebuilding each prompt from data/instances.jsonl.
    Returns replies imported. Run once, then delete the old files (migrate-then-delete)."""
    raise NotImplementedError
