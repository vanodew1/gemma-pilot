"""Keyword-search fault localization pilot.

Given only an issue's text, rank the repo's files so the file(s) the real fix
touched land near the top. This is step (A) of the proposed agent: search the
repo with keywords from the issue, then open only the matching files.
"""
import json
import math
import re
from dataclasses import dataclass

# How much a hit on each kind of keyword counts toward a file's score.
WEIGHTS = {"path": 5.0, "ident": 3.0, "error": 3.0, "word": 1.0}

STOPWORDS = set("""
a about above after again against all also am an and any are as at be because been
before being below between both but by can could did do does doing down during each
few for from further had has have having he her here hers him his how however i if in
into is it its itself just like me more most my no nor not now of off on once only or
other our out over own same she should so some such than that the their them then there
these they this those through to too under until up very was we were what when where
which while who whom why will with would you your yours
seems seem using used use want wants work works working expected expect instead think
actually still something anything problem issue issues example following trying tried
happen happens happened case cases would able need needs note version versions thanks
bug fix error errors exception raise raises raised get got gets make makes way
traceback recent call last line file files most python code instead return returned
none true false self cls def class import from print pass
""".split())

_TRACE_FRAME = re.compile(r'File "([^"]+\.py)", line \d+(?:, in (\w+))?')
_PY_PATH = re.compile(r"[\w./\\-]+\.py\b")
_EXC_LINE = re.compile(r"^\s*([A-Z]\w*(?:Error|Exception|Warning|Exit|Interrupt)):\s+(.+)$", re.M)
# Single quotes only count when not part of a contraction (I'm, it's).
_QUOTED = re.compile(r'"([^"\n]{8,120})"|(?<!\w)\'([^\'\n]{8,120})\'(?!\w)')
_BACKTICK = re.compile(r"`([^`\n]+)`")
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_WORD = re.compile(r"\b[A-Za-z]{4,}\b(?!['’]\w)")


@dataclass(frozen=True)
class Keyword:
    term: str
    kind: str  # one of WEIGHTS

    @property
    def weight(self):
        return WEIGHTS[self.kind]


def _repo_relative(path):
    """Strip install prefixes so a traceback path can match a repo file by suffix."""
    path = path.replace("\\", "/")
    for marker in ("site-packages/", "dist-packages/"):
        if marker in path:
            return path.rsplit(marker, 1)[1]
    return "/".join(path.split("/")[-2:])


def _is_code_shaped(token):
    return "_" in token or "." in token or bool(re.search(r"[a-z][A-Z]|[A-Z]{2,}[a-z]|[a-z][A-Z]{2,}", token))


def extract_keywords(text):
    """Deterministic keyword extraction from issue text.

    Kinds, strongest first: `path` (a .py file named in a traceback or the text),
    `ident` (code-shaped tokens, backticked code, traceback function names,
    exception names), `error` (quoted strings and exception messages, usually
    literal error text), `word` (remaining non-stopword English words).
    """
    found = {}  # term -> kind; first kind recorded wins, so add strongest first

    def add(term, kind):
        term = term.strip().strip(".,:;()[]{}'\"")
        if len(term) < 3 or term.lower() in STOPWORDS:
            return
        found.setdefault(term, kind)

    for path, func in _TRACE_FRAME.findall(text):
        add(_repo_relative(path), "path")
        if func and func != "<module>":
            add(func, "ident")
    for path in _PY_PATH.findall(text):
        add(_repo_relative(path), "path")

    code_spans = _BACKTICK.findall(text)
    candidates = [t for span in code_spans for t in _TOKEN.findall(span)]
    candidates += [t for t in _TOKEN.findall(text) if _is_code_shaped(t)]
    for exc, _ in _EXC_LINE.findall(text):
        candidates.append(exc)
    for token in candidates:
        if token.endswith(".py"):
            continue
        for part in token.split("."):
            if part and not part.isdigit():
                add(part, "ident")

    for exc, message in _EXC_LINE.findall(text):
        add(message.strip().strip("\"'"), "error")
    for a, b in _QUOTED.findall(text):
        quoted = a or b
        # Prose with spaces, not code: code is already covered by `ident`.
        if " " in quoted and not re.search(r"[=()\[\]{}]|\.py$", quoted):
            add(quoted, "error")

    prose = _TRACE_FRAME.sub(" ", text)
    prose = _PY_PATH.sub(" ", prose)
    for word in _WORD.findall(prose):
        if word not in found:
            add(word.lower(), "word")

    return [Keyword(term, kind) for term, kind in found.items()]


def _pattern(term):
    if " " in term:  # error strings: literal substring
        return re.compile(re.escape(term))
    return re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)")


def count_hits(keywords, files):
    """{term: {path: hit count}} for whole-word matches (like `rg -w -F`).

    `path` keywords match by filename suffix instead of by content.
    """
    hits = {}
    for k in keywords:
        if k.kind == "path":
            matched = {p: 1 for p in files if p == k.term or p.endswith("/" + k.term)}
        else:
            pat = _pattern(k.term)
            matched = {p: n for p, text in files.items() if (n := len(pat.findall(text)))}
        if matched:
            hits[k.term] = matched
    return hits


def rank_files(keywords, files, define_bonus=2.0):
    """Rank files by sum over keywords of weight * (log(1 + hits) + bonus) * idf.

    idf = log(1 + N / files_containing_term), so a term found in every file
    counts for little and a rare identifier counts for a lot. `bonus` is
    `define_bonus` when the file has `def <term>` or `class <term>`, so the
    file that defines a function beats big files that merely call it.
    Returns [(path, score)], best first, files with no hits omitted.
    """
    hits = count_hits(keywords, files)
    n = len(files)
    scores = {}
    for k in keywords:
        per_file = hits.get(k.term, {})
        idf = math.log(1 + n / len(per_file)) if per_file else 0.0
        defines = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+" + re.escape(k.term) + r"\b", re.M)
        for path, count in per_file.items():
            bonus = define_bonus if k.kind == "ident" and defines.search(files[path]) else 0.0
            scores[path] = scores.get(path, 0.0) + k.weight * (math.log(1 + count) + bonus) * idf
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def gold_files(patch):
    """Files the reference fix touched, read from the diff headers."""
    return set(re.findall(r"^diff --git a/(\S+) b/", patch, re.M))


def hit_at_k(ranked, gold, k):
    """True if at least one gold file is among the top k ranked files."""
    return bool(set(ranked[:k]) & gold)


def recall_at_k(ranked, gold, k):
    """Share of gold files found among the top k ranked files."""
    return len(set(ranked[:k]) & gold) / len(gold)


def parse_llm_keywords(reply):
    """Turn a model's reply (a JSON list of strings, maybe in a code fence) into Keywords.

    Kind comes from the string's shape: `.py` paths, multi-word error text, or
    identifiers; dotted names are split into their parts, as `extract_keywords` does.
    If the list isn't valid JSON (bad escapes, trailing chatter), the quoted strings
    inside it are used. Returns [] if the reply holds no list.
    """
    start = reply.find("[")
    if start < 0:
        return []
    end = reply.find("]", start)
    body = reply[start:end + 1] if end > 0 else reply[start:]
    try:
        terms = json.loads(body)
    except json.JSONDecodeError:
        terms = re.findall(r'"([^"\n]*)"', body)
    found = {}

    def add(term, kind):
        if len(term) >= 3 and term.lower() not in STOPWORDS:
            found.setdefault(term, kind)

    for term in terms:
        if not isinstance(term, str):
            continue
        term = term.strip()
        if term.endswith(".py"):
            add(_repo_relative(term), "path")
        elif " " in term:
            add(term, "error")
        else:
            for part in term.split("."):
                add(part, "ident")
    return [Keyword(t, k) for t, k in found.items()]
