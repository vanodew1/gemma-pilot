"""Ground-then-Choose file localization: every pure step, stdlib only.

Replaces pilot.py. This file is the single source for both callers:
  * the experiment harness (experiment.py / arms.py) imports it;
  * the Kaggle skill vendors a byte-identical copy at skills/fix/scripts/ground.py
    (tools/build_submission.py copies it; tests/test_vendor.py fails if they differ).

Rules for this module (enforced by tests/test_vendor.py, which imports it with
sys.modules stripped of everything outside the stdlib):
  * no third-party imports, no network, no model calls, no clock, no randomness
    without an explicit seed;
  * every model interaction is a `Question`: the exact prompt text plus the parser
    for the reply. Who sends the prompt (Oracle in the experiment, the ADK harness
    in the agent) is not this module's business.

Data flow for the agent path (identical to arm S1):
    read_tree(root) -> Files
    locate(issue, files) -> Menu          # K1 keywords -> rank_files -> top-5 + outlines
    menu.render() + CHOICE_INSTRUCTION    # what locate.py prints / what S1 embeds
    choice_question(issue, menu).parse(reply) -> Parsed[tuple[int, ...]]
    menu.order(labels) -> ranking         # Hit@k is computed on this
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, Iterable, Mapping, Sequence, TypeVar

A = TypeVar("A")

# A repo snapshot: repo-relative posix path -> source text. Only `is_source` files.
Files = Mapping[str, str]
# Best first, no duplicates, every entry a key of the Files it was ranked over.
Ranking = tuple[str, ...]

MENU_SIZE = 5


# --------------------------------------------------------------------------- keywords
# Moved verbatim from pilot.py (bodies unchanged): WEIGHTS, STOPWORDS, the regexes,
# Keyword, _repo_relative, _is_code_shaped, extract_keywords, _pattern, count_hits,
# rank_files, parse_llm_keywords. tests/test_pilot.py becomes tests/test_ground.py
# with only the import line changed.

WEIGHTS = {"path": 5.0, "ident": 3.0, "error": 3.0, "word": 1.0}


@dataclass(frozen=True)
class Keyword:
    term: str
    kind: str  # one of WEIGHTS

    @property
    def weight(self) -> float:
        return WEIGHTS[self.kind]


def extract_keywords(text: str) -> list[Keyword]:
    """K1: deterministic keywords from issue text (pilot.py, unchanged)."""
    raise NotImplementedError


def parse_llm_keywords(reply: str) -> list[Keyword]:
    """K2 reply -> typed keywords (pilot.py, unchanged)."""
    raise NotImplementedError


def count_hits(keywords: Sequence[Keyword], files: Files) -> dict[str, dict[str, int]]:
    raise NotImplementedError


def rank_files(keywords: Sequence[Keyword], files: Files, define_bonus: float = 2.0) -> list[tuple[str, float]]:
    raise NotImplementedError


def keyword_ranking(keywords: Sequence[Keyword], files: Files) -> Ranking:
    """rank_files without scores. The only ranking form the rest of the system sees."""
    return tuple(p for p, _ in rank_files(keywords, files))


def gold_files(patch: str) -> set[str]:
    """Files the reference fix touched (pilot.py, unchanged)."""
    raise NotImplementedError


def hit_at_k(ranked: Sequence[str], gold: set[str], k: int) -> bool:
    """(pilot.py, unchanged.) Contract: metric_contracts.hit_at_k_matches_definition."""
    raise NotImplementedError


def recall_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    """(pilot.py, unchanged.) Contract: metric_contracts.recall_is_a_fraction."""
    raise NotImplementedError


# --------------------------------------------------------------------------- repo reading
def is_test_path(path: str) -> bool:
    """test_*.py, *_test.py, conftest.py, or under tests/test/testing. Split out of
    run.is_source so finish.py drops exactly the files locate never searches."""
    raise NotImplementedError


def is_source(path: str) -> bool:
    """Searchable files (run.py rules): .py, not is_test_path, no docs/examples/vendored."""
    raise NotImplementedError


def read_tree(root: Path) -> dict[str, str]:
    """{posix relative path: text} for every `is_source` file under `root`'s working tree.

    The one loader for both callers: the sandbox repo is a checkout at base_commit, and
    Kaggle snapshots are git repos at base_commit, so neither needs git plumbing.
    Skips `.git/`. Decodes utf-8 with "replace" (same as run.files_at).
    """
    raise NotImplementedError


# --------------------------------------------------------------------------- outlines / windows
_OUTLINE = re.compile(r"^(\s*)(?:async\s+)?(def|class)\s+(\w+)", re.M)


def outline(text: str, max_names: int = 40) -> str:
    """Class names, functions, and methods in file order (experiments.py, unchanged).

    Regex over source, not graphs/<id>.json: the released graphs drop `async def`.
    """
    raise NotImplementedError


def windows(keywords: Sequence[Keyword], text: str, radius: int = 10, max_spans: int = 5) -> list[tuple[int, int]]:
    """Merged line ranges around strong keyword hits (run.py, unchanged). Used by `locate.py --open N`."""
    raise NotImplementedError


# --------------------------------------------------------------------------- the menu
@dataclass(frozen=True)
class Candidate:
    label: int  # 1-based number the model answers with
    path: str
    outline: str


@dataclass(frozen=True)
class Menu:
    """The grounded candidate set a model chooses from.

    Invariant (checked in build_menu): labels are 1..len(candidates), paths distinct.
    `render()` is the single text form: locate.py prints it, choice_question embeds it.
    """
    candidates: tuple[Candidate, ...]

    def render(self) -> str:
        """'[1] path\\n<outline>\\n\\n[2] ...' exactly as experiments.select built it."""
        raise NotImplementedError

    @property
    def pool(self) -> Ranking:
        """Candidate paths in label order. Hit@MENU_SIZE on this is the S-arm ceiling."""
        return tuple(c.path for c in self.candidates)

    def order(self, labels: Sequence[int]) -> Ranking:
        """Paths reordered by 0-based `labels` (a permutation from parse_order)."""
        return tuple(self.candidates[i].path for i in labels)


def build_menu(ranking: Ranking, files: Files, k: int = MENU_SIZE, rotate: int = 0) -> Menu:
    """Top-k of `ranking` with outlines. `rotate` cycles the presentation order
    (rotate=1 shows ranks 2,3,4,5,1) so voting arms can cancel position bias;
    the agent always uses rotate=0. Empty ranking -> empty Menu (caller decides).
    """
    raise NotImplementedError


def locate(issue: str, files: Files) -> Menu:
    """THE agent's grounding step and arm S1's pool: K1 keywords -> rank -> top-5 menu.

    locate.py calls exactly this; arms.S1 calls exactly this. Changing the agent's
    grounding without changing the measured arm is impossible by construction.
    """
    return build_menu(keyword_ranking(extract_keywords(issue), files), files)


# --------------------------------------------------------------------------- questions
@dataclass(frozen=True)
class Parsed(Generic[A]):
    """A reply parsed into a domain value. `ok=False` means the parser fell back
    (no list / no path found); the value is still usable, and the experiment counts it."""
    value: A
    ok: bool


@dataclass(frozen=True)
class Question(Generic[A]):
    """One model interaction, fully determined by its prompt.

    `kind` is metadata for logs and cache files; the cache key is the prompt text,
    so a prompt edit can never reuse a stale reply.
    """
    kind: str
    prompt: str
    parse: Callable[[str], Parsed[A]]


KEYWORDS_PROMPT = "..."  # run.GEMMA_PROMPT, unchanged text
PROBE_PROMPT = "..."     # experiments.PROBE_PROMPT, unchanged text
CHOICE_HEADER = "..."    # first paragraph of experiments.SELECT_PROMPT + "BUG REPORT:\n{issue}\n\nCANDIDATES:\n"
# Printed verbatim by locate.py after the menu, and the last line of every choice prompt.
CHOICE_INSTRUCTION = (
    "Order the candidates from most to least likely to contain the code that must change.\n"
    "Reply with only a JSON list of the candidate numbers, for example [2, 1, 3, 5, 4]."
)


def keyword_question(issue: str, files: Files) -> Question[list[Keyword]]:
    """K2: the model lists grep strings given the file list and the issue."""
    raise NotImplementedError


def choice_question(issue: str, menu: Menu) -> Question[tuple[int, ...]]:
    """S1/S2/votes: CHOICE_HEADER + menu.render() + CHOICE_INSTRUCTION.
    parse = parse_order(reply, len(menu.candidates)); ok iff the last list held a number."""
    raise NotImplementedError


def probe_question(repo: str, issue: str) -> Question[tuple[str, ...]]:
    """P: name the file from the issue alone. parse -> .py paths in reply order."""
    raise NotImplementedError


# --------------------------------------------------------------------------- reply parsing
def answer_list(reply: str) -> str | None:
    """Text of the last [...] in the reply (experiments.py, unchanged)."""
    raise NotImplementedError


def parse_order(reply: str, n: int) -> list[int]:
    """0-based permutation of range(n) from the reply's last list (experiments.py, unchanged).
    Contract: verification/metric_contracts.parse_order_is_a_permutation."""
    raise NotImplementedError


# --------------------------------------------------------------------------- rerankers
def named_first(ranked: Sequence[str], keywords: Sequence[Keyword]) -> list[str]:
    """N: files whose path the model wrote move to the front (experiments.py, unchanged).
    Contract: metric_contracts.named_first_is_a_permutation."""
    raise NotImplementedError


def resolve_paths(named: Iterable[str], files: Files) -> Ranking:
    """Map model-written paths onto repo files by suffix match (either direction), in
    the order named, deduplicated. Turns P into an ordinary Ranking so Hit@k applies;
    replaces experiments.probe_hit."""
    raise NotImplementedError


def borda(rankings: Sequence[Ranking]) -> Ranking:
    """Voting: Borda count over rankings (a file absent from a ranking scores 0 there);
    ties broken by first appearance in rankings[0]. Output is a permutation of the union.
    """
    raise NotImplementedError
