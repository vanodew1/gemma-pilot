import argparse, difflib, json, os, re, shutil, subprocess, sys, time
import requests

here = os.path.dirname(os.path.abspath(__file__))
repoSource = os.path.join(here, "demoRepo")
runsDir = os.path.join(here, "runs")
maxSteps = 15
maxAttempts = 3
useColor = sys.stdout.isatty()

def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if useColor else text

def show(tag, text, code="0"):
    print(paint(f"[{tag}]", code), text, flush=True)

def freshCopy(mode):
    workDir = os.path.join(runsDir, mode + "_repo")
    shutil.rmtree(workDir, ignore_errors=True)
    shutil.copytree(repoSource, workDir, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return workDir

def codeFiles(workDir):
    found = []
    for root, dirs, files in os.walk(workDir):
        dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
        for f in files:
            if f.endswith((".py", ".md")):
                found.append(os.path.relpath(os.path.join(root, f), workDir))
    return sorted(found)

def safePath(workDir, path):
    full = os.path.normpath(os.path.join(workDir, path))
    if not full.startswith(workDir):
        raise ValueError("path outside repo")
    return full

def toolListFiles(workDir, args):
    return "\n".join(codeFiles(workDir))

def toolReadFile(workDir, args):
    full = safePath(workDir, args["path"])
    with open(full) as f:
        lines = f.read().splitlines()
    return "\n".join(f"{i + 1}: {line}" for i, line in enumerate(lines))

def toolSearchCode(workDir, args):
    words = [w.lower() for w in re.findall(r"\w+", args["query"]) if len(w) > 2]
    if not words:
        return "empty query"
    hits = []
    for rel in codeFiles(workDir):
        if rel.endswith(".md"):
            continue
        with open(os.path.join(workDir, rel)) as f:
            for num, line in enumerate(f, 1):
                low = line.lower()
                score = sum(1 for w in words if w in low)
                if score:
                    hits.append((score, rel, num, line.rstrip()))
    hits.sort(key=lambda h: -h[0])
    if not hits:
        return "no matches"
    return "\n".join(f"{rel}:{num}: {line}" for score, rel, num, line in hits[:10])

def toolEditFile(workDir, args):
    full = safePath(workDir, args["path"])
    with open(full) as f:
        text = f.read()
    oldText = args["oldText"]
    count = text.count(oldText)
    if count == 0:
        return "edit failed: oldText not found, copy it exactly from the file"
    if count > 1:
        return "edit failed: oldText appears more than once, include more lines"
    with open(full, "w") as f:
        f.write(text.replace(oldText, args["newText"], 1))
    return "edit applied"

def runTests(workDir):
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=workDir, capture_output=True, text=True, timeout=60)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output[-1500:]

def toolRunTests(workDir, args):
    passed, output = runTests(workDir)
    return ("ALL TESTS PASSED\n" if passed else "TESTS FAILED\n") + output

toolBox = {
    "listFiles": (toolListFiles, "listFiles {}  : list the repo files"),
    "readFile": (toolReadFile, 'readFile {"path": "..."}  : show a file with line numbers'),
    "searchCode": (toolSearchCode, 'searchCode {"query": "words"}  : find matching lines across the repo'),
    "editFile": (toolEditFile, 'editFile {"path": "...", "oldText": "...", "newText": "..."}  : replace exact text in a file'),
    "runTests": (toolRunTests, "runTests {}  : run the test suite"),
}

def toolsFor(mode):
    names = ["listFiles", "readFile", "editFile"]
    if mode in ("search", "both"):
        names.insert(1, "searchCode")
    if mode in ("retry", "both"):
        names.append("runTests")
    return names

def systemPrompt(mode):
    names = toolsFor(mode)
    toolLines = "\n".join("- " + toolBox[n][1] for n in names)
    tips = []
    if "searchCode" in names:
        tips.append("Start by using searchCode with words from the issue to find the right place.")
    if "runTests" in names:
        tips.append("After editing, use runTests. If tests fail, read the error and fix again.")
    return f"""You are a coding agent fixing a bug in a small Python repo.
Each turn reply with exactly ONE JSON object and nothing else:
{{"thought": "short reason", "tool": "<name>", "args": {{...}}}}
When you think the bug is fixed, reply {{"thought": "...", "tool": "finish", "args": {{}}}}.
Available tools:
{toolLines}
- finish {{}}  : stop, your fix is done
Rules: change as little code as possible, never edit the tests.
{" ".join(tips)}"""

def callModel(messages, settings):
    response = requests.post(settings["url"].rstrip("/") + "/chat/completions", json={"model": settings["model"], "messages": messages, "temperature": 0.2}, headers={"Authorization": "Bearer " + settings["key"]}, timeout=300)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def parseAction(reply):
    cleaned = re.sub(r"```(json)?", "", reply)
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        for end in range(start, len(cleaned)):
            if cleaned[end] == "{":
                depth += 1
            elif cleaned[end] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        action = json.loads(cleaned[start:end + 1])
                        if isinstance(action, dict) and "tool" in action:
                            action.setdefault("args", {})
                            return action
                    except json.JSONDecodeError:
                        pass
                    break
        start = cleaned.find("{", start + 1)
    return None

def makeDiff(workDir):
    lines = []
    for rel in codeFiles(workDir):
        if rel.endswith(".md"):
            continue
        with open(os.path.join(repoSource, rel)) as f:
            before = f.read().splitlines()
        with open(os.path.join(workDir, rel)) as f:
            after = f.read().splitlines()
        lines += difflib.unified_diff(before, after, "a/" + rel, "b/" + rel, lineterm="")
    return "\n".join(lines)

def runAgent(mode, settings, replay=None):
    os.makedirs(runsDir, exist_ok=True)
    workDir = freshCopy(mode)
    with open(os.path.join(workDir, "ISSUE.md")) as f:
        issue = f.read()
    allowed = toolsFor(mode)
    messages = [{"role": "system", "content": systemPrompt(mode)}, {"role": "user", "content": "Fix this issue:\n\n" + issue}]
    replies = []
    replayQueue = list(replay or [])
    steps, toolCalls, attempt = 0, 0, 1
    started = time.time()
    print()
    show("mode", f"{mode}  (tools: {', '.join(allowed)})", "1;36")
    while steps < maxSteps:
        steps += 1
        if replay is not None:
            if not replayQueue:
                show("replay", "recording ran out", "33")
                break
            reply = replayQueue.pop(0)
        else:
            reply = callModel(messages, settings)
        replies.append(reply)
        messages.append({"role": "assistant", "content": reply})
        action = parseAction(reply)
        if action is None:
            show("agent", "reply was not valid JSON, asking again", "33")
            messages.append({"role": "user", "content": "Reply with one JSON object only."})
            continue
        tool = action["tool"]
        show("think", action.get("thought", ""), "2")
        if tool == "finish":
            if "runTests" in allowed:
                passed, output = runTests(workDir)
                if not passed and attempt < maxAttempts:
                    attempt += 1
                    show("retry", f"tests still failing, attempt {attempt} of {maxAttempts}", "1;33")
                    messages.append({"role": "user", "content": "Tests still fail, so the bug is not fixed:\n" + output + "\nFix it and try again."})
                    continue
            break
        if tool not in allowed:
            result = f"unknown tool '{tool}'. Use one of: {', '.join(allowed + ['finish'])}"
        else:
            toolCalls += 1
            try:
                result = toolBox[tool][0](workDir, action["args"])
            except Exception as e:
                result = f"error: {e}"
        show("tool", f"{tool} {json.dumps(action['args'])[:90]}", "34")
        preview = result if len(result) < 400 else result[:400] + " ..."
        print(paint("   " + preview.replace("\n", "\n   "), "2"))
        messages.append({"role": "user", "content": "Result of " + tool + ":\n" + result})
    passed, output = runTests(workDir)
    diff = makeDiff(workDir)
    print()
    show("patch", "", "1")
    print(diff or "(no changes)")
    verdict = paint("FIXED", "1;32") if passed else paint("NOT FIXED", "1;31")
    show("result", f"{verdict}  steps={steps} toolCalls={toolCalls} attempts={attempt} time={time.time() - started:.0f}s", "1")
    if replay is None:
        with open(os.path.join(runsDir, mode + "_log.json"), "w") as f:
            json.dump(replies, f, indent=1)
    return {"mode": mode, "fixed": passed, "steps": steps, "toolCalls": toolCalls, "attempts": attempt}

def main():
    parser = argparse.ArgumentParser(description="Mini developer agent demo: search + test-and-retry")
    parser.add_argument("--mode", choices=["baseline", "search", "retry", "both", "all"], default="both")
    parser.add_argument("--model", default=os.environ.get("DEMO_MODEL", "gemma4:12b"))
    parser.add_argument("--url", default=os.environ.get("DEMO_URL", "http://localhost:11434/v1"))
    parser.add_argument("--key", default=os.environ.get("DEMO_KEY", "none"))
    parser.add_argument("--replay", action="store_true", help="replay the saved run in runs/ instead of calling the model")
    args = parser.parse_args()
    settings = {"model": args.model, "url": args.url, "key": args.key}
    modes = ["baseline", "search", "retry", "both"] if args.mode == "all" else [args.mode]
    results = []
    for mode in modes:
        replay = None
        if args.replay:
            logPath = os.path.join(runsDir, mode + "_log.json")
            if not os.path.exists(logPath):
                show("replay", f"no saved run for {mode}, run it live once first", "31")
                continue
            with open(logPath) as f:
                replay = json.load(f)
        try:
            results.append(runAgent(mode, settings, replay))
        except requests.exceptions.ConnectionError:
            show("error", f"can't reach the model at {settings['url']}. Is Ollama running? (ollama serve)", "1;31")
            return
        except requests.exceptions.HTTPError as e:
            show("error", f"model server said: {e}. Check the model name with: ollama list", "1;31")
            return
    if len(results) > 1:
        print()
        print(f"{'mode':<10}{'fixed':<8}{'steps':<7}{'tools':<7}{'attempts'}")
        for r in results:
            print(f"{r['mode']:<10}{'yes' if r['fixed'] else 'no':<8}{r['steps']:<7}{r['toolCalls']:<7}{r['attempts']}")

if __name__ == "__main__":
    main()
