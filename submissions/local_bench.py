"""Local stand-in for Kaggle's harness, built from HARNESS_README.md.

Runs an agent prompt on dev tasks with a local Ollama Gemma model, in Kaggle's
sandbox image with no network, then scores the patch in a fresh container.

    python local_bench.py gold  --limit 2
    python local_bench.py agent --model gemma4:e4b --limit 5

Differences from Kaggle: Ollama Q4_K_M weights rather than QAT, a simplified
compaction, and no thinking-token cap. Compare versions against each other here;
the real score comes from Kaggle.
"""
from __future__ import annotations

import argparse
import ast
import collections
import concurrent.futures as cf
import difflib
import json
import random
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path(r"D:\AI Project\gemma-4-developer-agent")
OUT = Path(r"D:\AI Project\bench_runs")
AGENT_FILE = Path(__file__).with_name("agent_v1.py")
IMAGE = "swebench-bench:latest"  # swebench-sandbox plus the official wheels installed
OLLAMA = "http://127.0.0.1:11434/api/chat"
LLAMA = "http://127.0.0.1:8089/v1/chat/completions"
BACKEND = "ollama"
SEED = 42
SEALED_REPO = "Textualize/rich"

MAX_STDOUT = 5000
MAX_FILE_LINES = 150
MAX_FILE_CHARS = 10000
VERIFY_TIMEOUT = 300
COMPACT_TOKENS = 14336
COMPACT_KEEP = 5
NUDGE = "Please continue your work using the available tools, or call submit_patch when you have completed and verified your changes."

PROTECTED = re.compile(
    r"(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py|pytest\.ini|pyproject\.toml|tox\.ini|setup\.cfg"
    r"|\.pytest\.ini|sitecustomize\.py|usercustomize\.py|_swegemma_stubs\.py|[^/]*\.pth)$"
    r"|(^|/)(tests|test|testing)/.*\.py$"
)


def load_agent(path: Path) -> tuple[str, dict, list | None]:
    """Read the prompt, budget and (for staged agents) the step list from an agent_vN.py file."""
    constants = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name.endswith("_PROMPT") or name in ("EVAL_CONFIG_YAML", "STAGES"):
                constants[name] = ast.literal_eval(node.value)
    budget = {k: float(v) for k, v in re.findall(r"(\w+): ([\d.]+)", constants["EVAL_CONFIG_YAML"])}
    stages = constants.get("STAGES")
    if stages:
        stages = [{**s, "prompt": constants[s["prompt"]]} for s in stages]
    return constants.get("SYSTEM_PROMPT", ""), budget, stages


def fill(template: str, task: dict, state: dict) -> str:
    """Fill {problem_description} and ADK-style {key?} templates from session state."""
    text = template.replace("{problem_description}", task["problem_statement"])
    return re.sub(r"\{(\w+)\?\}", lambda m: state.get(m.group(1), ""), text)


def load_tasks() -> list[dict]:
    with open(DATA / "tasks.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def eval_tasks(tasks: list[dict]) -> list[dict]:
    """The same fixed 40 tasks agent_v1.py selects in the notebook."""
    rng = random.Random(20261110)
    by_id = lambda t: t["instance_id"]
    fastapi = sorted((t for t in tasks if t["repo"] == "fastapi/fastapi"), key=by_id)
    others = sorted((t for t in tasks if t["repo"] in ("psf/requests", "encode/httpx")), key=by_id)
    chosen = rng.sample(fastapi, 26) + others
    rng.shuffle(chosen)
    return chosen


class Box:
    """One no-network container holding one task's repository."""

    def __init__(self, task: dict):
        self.name = f"bench_{task['instance_id']}_{uuid.uuid4().hex[:8]}"
        self.task = task
        mounts = [
            ("wheels", DATA / "wheels", "/wheels"),
            ("sandbox", DATA / "sandbox", "/sandbox"),
            ("snapshot", DATA / "snapshots" / f"{task['instance_id']}.tgz", "/snap.tgz"),
        ]
        cmd = ["docker", "run", "-d", "--rm", "--name", self.name, "--network", "none",
               "--memory", "4g", "--cpus", "2"]
        for _, source, target in mounts:
            cmd += ["--mount", f"type=bind,source={source},target={target},readonly"]
        subprocess.run(cmd + [IMAGE, "sleep", "infinity"], check=True, capture_output=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

    def sh(self, command: str, timeout: int = 300, stdin: bytes | None = None) -> tuple[int, str, str]:
        wrapped = ["docker", "exec", "-i", "-w", "/workspace", self.name,
                   "timeout", "-k", "5", str(timeout), "bash", "-c", command]
        try:
            r = subprocess.run(wrapped, input=stdin, capture_output=True, timeout=timeout + 20)
        except subprocess.TimeoutExpired:
            return 124, "", f"timed out after {timeout}s"
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

    def read(self, rel: str) -> str | None:
        r = subprocess.run(["docker", "exec", self.name, "cat", "--", f"/workspace/{rel}"], capture_output=True)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None

    def write(self, rel: str, text: str) -> None:
        subprocess.run(
            ["docker", "exec", "-i", self.name, "bash", "-c",
             'mkdir -p "$(dirname "$1")" && cat > "$1"', "_", f"/workspace/{rel}"],
            input=text.encode("utf-8"), check=True, capture_output=True)

    def prepare(self, message: str) -> None:
        steps = [
            "git config --global --add safe.directory '*'",
            "tar xzf /snap.tgz --no-same-owner -C /workspace",
            "pip install -q --no-index --find-links=/wheels --no-build-isolation -e /workspace 2>&1 | tail -3; true",
            f"python3 /sandbox/setup.py {self.task['repo']} --fast-path --workspace /workspace",
            f"git add -A && git commit -m {message} --allow-empty -q",
        ]
        for step in steps:
            rc, out, err = self.sh(step, timeout=280)
            if rc != 0:
                raise RuntimeError(f"setup failed: {step}: {err[-400:] or out[-400:]}")

    def diff(self) -> str:
        self.sh("git add -N .")
        _, out, _ = self.sh("git diff --binary HEAD")
        return strip_protected(out)


def strip_protected(patch: str) -> str:
    if "diff --git " not in patch:
        return patch
    kept = []
    for section in re.split(r"(?m)^(?=diff --git )", patch):
        header = re.match(r"diff --git a/(\S+) b/(\S+)", section)
        if section and not (header and PROTECTED.search(header.group(2))):
            kept.append(section)
    return "".join(kept)


def apply_patch(box: Box, path: str) -> bool:
    attempts = [
        f"git apply --unsafe-paths {path}",
        f"git apply -3 {path}",
        f"git apply --ignore-space-change --ignore-whitespace {path}",
        f"git apply --recount {path}",
        f"patch -p1 --dry-run --batch --forward < {path} && patch -p1 --batch --forward < {path}",
        f"patch -p1 --dry-run --batch --forward -l < {path} && patch -p1 --batch --forward -l < {path}",
    ]
    return any(box.sh(a, timeout=60)[0] == 0 for a in attempts)


def changed_files(patch: str) -> list[str]:
    paths = re.findall(r"^\+\+\+ b/(\S+)", patch, re.M)
    return sorted(set(paths))


def verify(task: dict, patch: str) -> dict:
    """Phase 2: fresh container, agent patch, official tests, pytest."""
    result = {"resolved": False, "exit_code": None, "passed": 0, "failed": 0, "error": ""}
    patch = strip_protected(patch)
    if not patch.strip():
        result["error"] = "empty patch"
        return result
    with Box(task) as box:
        box.prepare("eval_baseline")
        box.sh("cat > /tmp/agent.patch", stdin=(patch.rstrip("\n") + "\n").encode("utf-8"))
        if not apply_patch(box, "/tmp/agent.patch"):
            result["error"] = "agent patch did not apply"
            return result
        test_files = changed_files(task["test_patch"])
        quoted = " ".join(f"'{p}'" for p in test_files)
        box.sh(f"git checkout HEAD -- {quoted} 2>/dev/null; git clean -f -- {quoted} 2>/dev/null; true")
        box.sh("cat > /tmp/test.patch", stdin=(task["test_patch"].rstrip("\n") + "\n").encode("utf-8"))
        if not apply_patch(box, "/tmp/test.patch"):
            result["error"] = "test patch did not apply"
            return result
        targets = " ".join(f"'{p}'" for p in test_files if p.endswith(".py"))
        rc, out, err = box.sh(
            "PYTHONSAFEPATH=1 PYTHONNOUSERSITE=1 python3 -s -m pytest "
            f"{targets} --junitxml=/tmp/junit.xml -p no:anyio -o timeout=0 "
            "-o python_classes='Test* *Test' -q",
            timeout=VERIFY_TIMEOUT)
        result["exit_code"] = rc
        result["output_tail"] = (out + err)[-1500:]
        _, xml, _ = box.sh("cat /tmp/junit.xml")
        try:
            root = ET.fromstring(xml)
            suites = [root] if root.tag == "testsuite" else list(root)
            tests = sum(int(s.get("tests", 0)) for s in suites)
            failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
            skipped = sum(int(s.get("skipped", 0)) for s in suites)
            result["passed"], result["failed"] = tests - failed - skipped, failed
        except ET.ParseError:
            result["error"] = "no junit report"
        result["resolved"] = rc == 0 and result["passed"] > 0 and result["failed"] == 0
    return result


TOOLS = [
    ("run_command", "Run a shell command in /workspace.", {"command": "string"}, ["command"]),
    ("read_file", "Read a file from /workspace, at most 150 lines per call.",
     {"filepath": "string", "start_line": "integer", "end_line": "integer"}, ["filepath"]),
    ("edit_file", "Replace old_string with new_string in an existing file.",
     {"filepath": "string", "old_string": "string", "new_string": "string", "allow_multiple": "boolean"},
     ["filepath", "old_string", "new_string"]),
    ("write_file", "Create or overwrite a file in /workspace.", {"filepath": "string", "content": "string"},
     ["filepath", "content"]),
    ("get_status", "Show budget use and patch status.", {}, []),
    ("submit_patch", "Submit the current changes as the final patch.", {}, []),
]
TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": n, "description": d, "parameters": {
        "type": "object", "properties": {k: {"type": v} for k, v in p.items()}, "required": r}}}
    for n, d, p, r in TOOLS
]


def clean_path(raw: str) -> str:
    rel = str(raw).strip()
    for prefix in ("/workspace/", "/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
    if ".." in Path(rel).parts:
        raise ValueError("path traversal is not allowed")
    return rel


def error(kind: str, message: str, **details) -> str:
    return json.dumps({"status": "error", "error_type": kind, "error_message": message, "details": details})


def replace_regex(text: str, old: str, new: str, allow_multiple: bool) -> tuple[str, int, str]:
    """Kaggle's third matching tier: tokens around code delimiters, any whitespace between."""
    tokens = re.findall(r"[():\[\]{}>=<]|[^\s():\[\]{}>=<]+", old)
    matches = list(re.finditer(r"\s*".join(map(re.escape, tokens)), text)) if tokens else []
    if not matches:
        raise ValueError("old_string not found")
    if len(matches) > 1 and not allow_multiple:
        raise ValueError(f"old_string matches {len(matches)} places; make it unique")
    for match in reversed(matches):
        line = text[text.rfind("\n", 0, match.start()) + 1:match.start()]
        indent = line[:len(line) - len(line.lstrip())]
        new_lines = new.strip("\n").split("\n")
        base = len(new_lines[0]) - len(new_lines[0].lstrip())
        rest = [indent + l[base:] if l.strip() else l for l in new_lines[1:]]
        text = text[:match.start()] + "\n".join([new_lines[0].lstrip()] + rest) + text[match.end():]
    return text, len(matches), "regex"


def replace_text(text: str, old: str, new: str, allow_multiple: bool) -> tuple[str, int, str]:
    text = text.replace("\r\n", "\n")
    count = text.count(old)
    if count:
        if count > 1 and not allow_multiple:
            raise ValueError(f"old_string matches {count} places; make it unique")
        return text.replace(old, new), count, "exact"
    lines, want = text.split("\n"), [l.strip() for l in old.strip("\n").split("\n")]
    hits = [i for i in range(len(lines) - len(want) + 1)
            if [l.strip() for l in lines[i:i + len(want)]] == want]
    if not hits:
        return replace_regex(text, old, new, allow_multiple)
    if len(hits) > 1 and not allow_multiple:
        raise ValueError(f"old_string matches {len(hits)} places; make it unique")
    for i in reversed(hits):
        indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
        new_lines = new.strip("\n").split("\n")
        base = len(new_lines[0]) - len(new_lines[0].lstrip())
        lines[i:i + len(want)] = [indent + l[base:] if l.strip() else l for l in new_lines]
    return "\n".join(lines), len(hits), "flexible"


class Session:
    def __init__(self, box: Box, budget: dict):
        self.box, self.budget = box, budget
        self.calls, self.patch, self.submitted = 0, "", False
        self.start = time.time()
        self.time_limit = budget["max_time_minutes"] * 60

    def remaining(self) -> float:
        return self.time_limit - (time.time() - self.start)

    def call(self, name: str, args: dict, allowed: list | None = None) -> str:
        if allowed is not None and name not in allowed:
            return error("UnknownTool", f"No tool named {name}")
        if self.remaining() <= 0:
            return error("BudgetExceeded", "Time budget exhausted")
        free = name in ("submit_patch", "get_status")
        if not free and self.calls >= self.budget["max_tool_calls"]:
            return error("BudgetExceeded", f"Tool call budget exhausted ({int(self.budget['max_tool_calls'])} calls)")
        if not free:
            self.calls += 1
        try:
            return self.add_warning(getattr(self, f"tool_{name}")(**args))
        except AttributeError:
            return error("UnknownTool", f"No tool named {name}")
        except (TypeError, ValueError) as exc:
            return error("ValidationError", str(exc))

    def add_warning(self, response: str) -> str:
        left = self.budget["max_tool_calls"] - self.calls
        if self.budget["max_tool_calls"] >= 20 and left <= 10:
            data = json.loads(response)
            data["budget_warning"] = f"Only {int(left)} tool call(s) remaining. Finalize your edits and call submit_patch soon."
            return json.dumps(data)
        return response

    def tool_run_command(self, command: str) -> str:
        limit = int(min(self.budget["timeout_seconds"], max(5, self.remaining())))
        rc, out, err = self.box.sh(str(command), timeout=limit)
        out, err = out[:MAX_STDOUT], err[:MAX_STDOUT]
        if rc == 124:
            return error("TimeoutExceeded", f"Command exceeded {limit}s", stdout=out, stderr=err)
        if rc != 0:
            return error("CommandError", f"Exit code {rc}", stdout=out, stderr=err, exit_code=rc)
        return json.dumps({"status": "ok", "stdout": out, "stderr": err, "exit_code": 0})

    def tool_read_file(self, filepath: str, start_line=None, end_line=None) -> str:
        rel = clean_path(filepath)
        text = self.box.read(rel)
        if text is None:
            return error("FileNotFound", f"Cannot read {rel}")
        lines = text.split("\n")
        start = max(1, int(start_line or 1))
        end = min(len(lines), int(end_line) if end_line else len(lines))
        end = min(end, start + MAX_FILE_LINES - 1)
        content, used = "", start - 1
        for line in lines[start - 1:end]:
            if len(content) + len(line) + 1 > MAX_FILE_CHARS:
                break
            content += line + "\n"
            used += 1
        return json.dumps({"status": "ok", "filepath": rel, "content": content, "start_line": start,
                           "end_line": used, "total_lines": len(lines), "is_truncated": used < len(lines)})

    def tool_edit_file(self, filepath: str, old_string: str, new_string: str, allow_multiple=False) -> str:
        rel = clean_path(filepath)
        text = self.box.read(rel)
        if not text or not old_string:
            return error("FileEditError", "File is missing or empty, or old_string is empty")
        multiple = str(allow_multiple).lower() == "true"
        try:
            updated, count, strategy = replace_text(text, old_string, new_string, multiple)
        except ValueError as exc:
            return error("FileEditError", str(exc))
        self.box.write(rel, updated)
        diff = "\n".join(difflib.unified_diff(text.split("\n"), updated.split("\n"),
                                              f"a/{rel}", f"b/{rel}", lineterm=""))
        return json.dumps({"status": "ok", "filepath": rel, "occurrences": count, "strategy": strategy,
                           "diff": diff[:MAX_STDOUT], "is_truncated": len(diff) > MAX_STDOUT})

    def tool_write_file(self, filepath: str, content: str) -> str:
        rel = clean_path(filepath)
        self.box.write(rel, str(content))
        return json.dumps({"status": "ok", "filepath": rel, "size": len(str(content))})

    def tool_get_status(self) -> str:
        return json.dumps({"status": "ok", "tool_calls_used": self.calls, "patch_submitted": self.submitted,
                           "tool_calls_remaining": int(self.budget["max_tool_calls"] - self.calls),
                           "time_seconds_remaining": round(self.remaining(), 1)})

    def tool_submit_patch(self) -> str:
        self.patch, self.submitted = self.box.diff(), True
        return json.dumps({"status": "ok", "patch_size": len(self.patch),
                           "files_changed": self.patch.count("diff --git ")})


def first_message(task: dict, budget: dict, box: Box) -> str:
    _, tree, _ = box.sh(
        "find . -mindepth 1 -maxdepth 3 -not -path '*/.*' -not -name '*.pyc' -not -path '*/__pycache__*' "
        "-not -path './docs/*' -not -path './docs_src/*' -not -path './tests/*' | sort | head -200")
    return f"""You are evaluating a software engineering task for repository {task['repo']}.

Problem Statement:
{task['problem_statement']}

## Task Budget (Session terminates when any budget is exhausted)
- Time allowance: {budget['max_time_minutes']} minutes
- Tool calls allowance: {int(budget['max_tool_calls'])} calls
- Max loop iterations: {int(budget['max_turns'])} turns

## Execution Environment Rules
- Single command timeout: {int(budget['timeout_seconds'])} seconds (commands exceeding this fail without ending the session)
- Command output limit: {MAX_STDOUT} characters
- File view limit: {MAX_FILE_LINES} lines per read_file call
- File character limit: {MAX_FILE_CHARS} characters per read_file call
- Environment is offline (no network/PyPI access). All repository and test dependencies are ALREADY pre-installed. Do NOT attempt to run pip install or download packages.

Work only under /workspace. Inspect existing conventions, verify your implementation using targeted tests or inline assertions before submitting, then call submit_patch.

## Workspace Layout
{tree}"""


def schemas(tools: list | None) -> list:
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in tools] if tools else TOOL_SCHEMAS


def chat_llama(messages: list, timeout: float, tools: list | None = None, params: dict | None = None) -> dict:
    """Call a local llama-server and return the reply in the shape Ollama uses."""
    converted, pending = [], []
    for index, message in enumerate(messages):
        if message["role"] == "assistant":
            item = {"role": "assistant", "content": message.get("content") or ""}
            if message.get("thinking"):
                item["reasoning_content"] = message["thinking"]
            if message.get("tool_calls"):
                pending = [f"call_{index}_{n}" for n in range(len(message["tool_calls"]))]
                item["tool_calls"] = [
                    {"id": cid, "type": "function",
                     "function": {"name": c["function"]["name"], "arguments": json.dumps(c["function"].get("arguments") or {})}}
                    for cid, c in zip(pending, message["tool_calls"])]
            converted.append(item)
        elif message["role"] == "tool":
            converted.append({"role": "tool", "tool_call_id": pending.pop(0) if pending else f"call_{index}",
                              "content": message["content"]})
        else:
            converted.append({"role": message["role"], "content": message["content"]})
    p = {"temperature": 0.2, "seed": SEED, "max_tokens": 4096, "think": True, **(params or {})}
    body = {"messages": converted, "tools": schemas(tools), "stream": False, "max_tokens": p["max_tokens"],
            "temperature": p["temperature"], "top_p": 0.95, "seed": p["seed"],
            "chat_template_kwargs": {"enable_thinking": p["think"]}}
    request = urllib.request.Request(LLAMA, json.dumps(body).encode("utf-8"), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read())
    choice = data["choices"][0]["message"]
    calls = []
    for call in choice.get("tool_calls") or []:
        try:
            arguments = json.loads(call["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        calls.append({"function": {"name": call["function"]["name"], "arguments": arguments}})
    timings = data.get("timings", {})
    return {"message": {"role": "assistant", "content": choice.get("content") or "",
                        "thinking": choice.get("reasoning_content") or "", "tool_calls": calls},
            "eval_count": data.get("usage", {}).get("completion_tokens", 0),
            "eval_duration": timings.get("predicted_ms", 0) * 1e6,
            "prompt_eval_count": data.get("usage", {}).get("prompt_tokens", 0)}


def chat(model: str, messages: list, timeout: float, tools: list | None = None, params: dict | None = None) -> dict:
    if BACKEND == "llama":
        return chat_llama(messages, timeout, tools, params)
    p = {"temperature": 0.2, "seed": SEED, "max_tokens": 4096, "think": True, **(params or {})}
    body = {"model": model, "messages": messages, "tools": schemas(tools), "stream": False, "think": p["think"],
            "keep_alive": "30m",
            "options": {"num_ctx": 32768, "num_predict": p["max_tokens"], "temperature": p["temperature"],
                        "top_p": 0.95, "seed": p["seed"],
                        "use_mmap": False, "num_gpu": 999}}  # keep the model in VRAM, not system RAM
    request = urllib.request.Request(OLLAMA, json.dumps(body).encode("utf-8"), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def compact(messages: list) -> None:
    for message in messages[2:-COMPACT_KEEP]:
        if message["role"] != "tool":
            continue
        try:
            old = json.loads(message["content"])
        except (json.JSONDecodeError, TypeError):
            old = {}
        short = {"status": old.get("status", "ok"), "note": "older output removed"}
        for key in ("error_type", "error_message"):
            if key in old:
                short[key] = old[key]
        message["content"] = json.dumps(short)


PEEK = re.compile(r"/wheels|site-packages|dist-packages|\.whl\b|pip (show|download)|importlib\.metadata")


def peeked_outside(messages: list) -> bool:
    """True if any tool call looked at installed packages, where newer releases may already hold the fix."""
    for message in messages:
        for call in message.get("tool_calls") or []:
            if PEEK.search(json.dumps(call["function"].get("arguments") or {})):
                return True
    return False


def run_staged(task: dict, stages: list, budget: dict, model: str, run_dir: Path) -> dict:
    """Run a SequentialAgent: each step runs until it replies without a tool call.

    A step with history sees the harness's first message and its own turns; a step without
    history (include_contents: none) sees only its filled instruction. A step's last text is
    stored under its output_key for later {key?} templates. Budgets are shared by all steps.
    """
    with Box(task) as box:
        box.prepare("baseline")
        session = Session(box, budget)
        state, trace, per_stage = {}, [], {}
        turns = tokens = 0
        gen_seconds = 0.0
        ended = "all steps done"
        for stage in stages:
            system = fill(stage["prompt"], task, state)
            opener = first_message(task, budget, box) if stage["history"] else "Begin."
            messages = [{"role": "system", "content": system}, {"role": "user", "content": opener}]
            params = {k: stage[k] for k in ("temperature", "max_tokens", "think")}
            params["seed"] = stage["seed"] + SEED - 42  # --seed shifts every step's seed, so runs differ
            calls_before, text = session.calls, ""
            while True:
                if session.remaining() <= 0:
                    ended = f"time limit in {stage['name']}"
                    break
                if turns >= budget["max_turns"]:
                    ended = f"turn limit in {stage['name']}"
                    break
                turns += 1
                try:
                    reply = chat(model, messages, max(10, session.remaining() + 5), stage["tools"], params)
                except (TimeoutError, urllib.error.URLError) as exc:
                    ended = f"model call ended in {stage['name']}: {exc}"
                    break
                tokens += reply.get("eval_count", 0)
                gen_seconds += reply.get("eval_duration", 0) / 1e9
                if reply.get("prompt_eval_count", 0) > COMPACT_TOKENS:
                    compact(messages)
                message = reply["message"]
                calls = message.get("tool_calls") or []
                messages.append({k: v for k, v in message.items() if v})
                for call in calls:
                    name, args = call["function"]["name"], call["function"].get("arguments") or {}
                    messages.append({"role": "tool", "tool_name": name,
                                     "content": session.call(name, args, stage["tools"])})
                if not calls:
                    text = (message.get("content") or "").strip()
                    break
                if session.submitted:
                    break
            if stage["output_key"]:
                state[stage["output_key"]] = text
            per_stage[stage["name"]] = {"tool_calls": session.calls - calls_before, "text": text[:300]}
            trace.append({"stage": stage["name"], "messages": messages})
            if ended != "all steps done":
                break
        if session.submitted:
            ended = "submitted"
        patch = session.patch if session.submitted else box.diff()
        record = {"instance_id": task["instance_id"], "repo": task["repo"], "ended": ended,
                  "peeked": any(peeked_outside(t["messages"]) for t in trace),
                  "submitted": session.submitted, "patch_chars": len(patch), "tool_calls": session.calls,
                  "turns": turns, "agent_seconds": round(time.time() - session.start, 1), "output_tokens": tokens,
                  "tokens_per_second": round(tokens / gen_seconds, 1) if gen_seconds else 0,
                  "stages": per_stage}
    (run_dir / "traces" / f"{task['instance_id']}.json").write_text(json.dumps(trace, indent=1), encoding="utf-8")
    (run_dir / "patches" / f"{task['instance_id']}.patch").write_bytes(patch.encode("utf-8"))
    return record


def run_agent(task: dict, prompt: str, budget: dict, model: str, run_dir: Path) -> dict:
    with Box(task) as box:
        box.prepare("baseline")
        session = Session(box, budget)
        system = prompt.replace("{problem_description}", task["problem_statement"])
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": first_message(task, budget, box)}]
        turns = nudges = tokens = 0
        gen_seconds = 0.0
        ended = "turn limit"
        while turns < budget["max_turns"]:
            if session.remaining() <= 0:
                ended = "time limit"
                break
            turns += 1
            try:
                reply = chat(model, messages, max(10, session.remaining() + 5))
            except (TimeoutError, urllib.error.URLError) as exc:
                ended = f"model call ended: {exc}"
                break
            tokens += reply.get("eval_count", 0)
            gen_seconds += reply.get("eval_duration", 0) / 1e9
            if reply.get("prompt_eval_count", 0) > COMPACT_TOKENS:
                compact(messages)
            message = reply["message"]
            calls = message.get("tool_calls") or []
            messages.append({k: v for k, v in message.items() if v})
            for call in calls:
                name, args = call["function"]["name"], call["function"].get("arguments") or {}
                messages.append({"role": "tool", "tool_name": name, "content": session.call(name, args)})
            if session.submitted:
                ended = "submitted"
                break
            nudges = 0 if calls else nudges + 1
            if nudges > 3:
                ended = "ran out of nudges"
                break
            if not calls:
                messages.append({"role": "user", "content": NUDGE})
        patch = session.patch if session.submitted else box.diff()
        record = {"instance_id": task["instance_id"], "repo": task["repo"], "ended": ended,
                  "peeked": peeked_outside(messages),
                  "submitted": session.submitted, "patch_chars": len(patch), "tool_calls": session.calls,
                  "turns": turns, "agent_seconds": round(time.time() - session.start, 1), "output_tokens": tokens,
                  "tokens_per_second": round(tokens / gen_seconds, 1) if gen_seconds else 0}
    (run_dir / "traces" / f"{task['instance_id']}.json").write_text(json.dumps(messages, indent=1), encoding="utf-8")
    (run_dir / "patches" / f"{task['instance_id']}.patch").write_bytes(patch.encode("utf-8"))
    return record


def safely(function, task: dict) -> dict:
    try:
        return function(task)
    except Exception as exc:  # one broken task must not end a whole run
        return {"instance_id": task["instance_id"], "repo": task["repo"], "resolved": False,
                "error": f"{type(exc).__name__}: {exc}"}


def finish(rows: list[dict], run_dir: Path) -> None:
    per_repo = collections.defaultdict(lambda: [0, 0])
    for row in rows:
        per_repo[row["repo"]][1] += 1
        per_repo[row["repo"]][0] += bool(row.get("resolved")) and not row.get("peeked")
    resolved = sum(bool(r.get("resolved")) and not r.get("peeked") for r in rows)
    peeked = [r["instance_id"] for r in rows if r.get("resolved") and r.get("peeked")]
    summary = {"resolved": resolved, "total": len(rows), "per_repo": dict(per_repo), "peeked_not_counted": peeked}
    (run_dir / "results.json").write_text(json.dumps({"summary": summary, "tasks": rows}, indent=1), encoding="utf-8")
    print(f"\nRESOLVED {resolved}/{len(rows)}  {dict(per_repo)}"
          f"{f'  (not counted, read installed packages: {peeked})' if peeked else ''}\nSaved to {run_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["gold", "agent"])
    parser.add_argument("--model", default="gemma4:e4b")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--workers", type=int, default=3, help="containers at once in gold mode")
    parser.add_argument("--all-unsealed", action="store_true", help="use all tasks outside the sealed repo")
    parser.add_argument("--all", action="store_true", help="use all 129 dev tasks, rich included")
    parser.add_argument("--agent-file", type=Path, default=AGENT_FILE)
    parser.add_argument("--repo", help="only tasks from this repository, such as psf/requests")
    parser.add_argument("--gold-results", nargs="*", type=Path, default=[],
                        help="results.json files from gold runs; keep only tasks whose correct fix passed")
    parser.add_argument("--backend", choices=["ollama", "llama"], default="ollama",
                        help="llama uses a llama-server already running on port 8089")
    parser.add_argument("--seed", type=int, default=42, help="sampling seed; vary it to measure luck")
    parser.add_argument("--time-minutes", type=float, help="override max_time_minutes, to see what a slow model could fix")
    args = parser.parse_args()
    global BACKEND, SEED
    BACKEND, SEED = args.backend, args.seed

    tasks = load_tasks()
    if args.all:
        chosen = tasks
    else:
        chosen = [t for t in tasks if t["repo"] != SEALED_REPO] if args.all_unsealed else eval_tasks(tasks)
        assert all(t["repo"] != SEALED_REPO for t in chosen), "sealed repo must stay out"
    if args.repo:
        chosen = [t for t in chosen if t["repo"] == args.repo]
    if args.gold_results:
        gradable = set()
        for path in args.gold_results:
            with open(path, encoding="utf-8") as f:
                gradable |= {r["instance_id"] for r in json.load(f)["tasks"] if r.get("resolved")}
        chosen = [t for t in chosen if t["instance_id"] in gradable]
    chosen = chosen[: args.limit]

    label = args.mode if args.mode == "gold" else f"{args.model.replace(':', '-')}-{args.agent_file.stem}-s{args.seed}"
    if args.time_minutes:
        label += f"-t{args.time_minutes:g}"
    run_dir = OUT / f"{time.strftime('%Y%m%d-%H%M%S')}-{label}"
    (run_dir / "traces").mkdir(parents=True)
    (run_dir / "patches").mkdir()

    if args.mode == "gold":
        def gold(task):
            return {"instance_id": task["instance_id"], "repo": task["repo"], **verify(task, task["patch"])}
        rows = []
        with cf.ThreadPoolExecutor(args.workers) as pool:
            for row in pool.map(lambda t: safely(gold, t), chosen):
                rows.append(row)
                print(row["instance_id"], "resolved" if row["resolved"] else f"FAILED {row.get('error', '')} "
                      f"exit={row.get('exit_code')} passed={row.get('passed')} failed={row.get('failed')}", flush=True)
        finish(rows, run_dir)
        return

    prompt, budget, stages = load_agent(args.agent_file)
    if args.time_minutes:
        budget["max_time_minutes"] = args.time_minutes
    def run_one(task):
        if stages:
            record = run_staged(task, stages, budget, args.model, run_dir)
        else:
            record = run_agent(task, prompt, budget, args.model, run_dir)
        patch = (run_dir / "patches" / f"{task['instance_id']}.patch").read_bytes().decode("utf-8")
        return {**record, **verify(task, patch)}
    rows = []
    for task in chosen:
        row = safely(run_one, task)
        row.pop("output_tail", None)
        rows.append(row)
        print({k: row.get(k) for k in ("instance_id", "resolved", "ended", "patch_chars", "tool_calls",
                                       "agent_seconds", "tokens_per_second", "error")}, flush=True)
    finish(rows, run_dir)


if __name__ == "__main__":
    main()
