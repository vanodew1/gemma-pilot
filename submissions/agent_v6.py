"""Agent v6 for the Gemma 4 Developer Agent Competition: solver plus two locked checks.

Four steps run in order for every bug:
  solve     the v1 guide, unchanged except it cannot submit and ends with a short note
  gate_a    starts clean, checks the edit exists and still compiles, repairs only real breakage
  gate_b    the same check again with a different seed, also sees gate_a's report
  finalize  the only step that can call submit_patch

Paste into one Kaggle notebook cell to write the agent and /kaggle/working/submission.zip.
local_bench.py reads SOLVE_PROMPT, GATE_PROMPT, FINALIZE_PROMPT, STAGES and EVAL_CONFIG_YAML from here.
"""
import os
import shutil
from pathlib import Path

MODEL = "gemma-4-e4b-it-qat-w4a16-ct"
WORK = Path(os.environ.get("SUBMISSION_WORKDIR", "/kaggle/working"))
AGENT_DIR = WORK / "sample_submission"

EVAL_CONFIG_YAML = """\
evaluation:
  timeout_seconds: 75
  max_tool_calls: 50
  max_time_minutes: 4.5
  max_turns: 120
"""

SOLVE_PROMPT = """\
You are fixing one issue in the repository at /workspace. You have about 4 minutes, so act quickly and keep your reasoning to a few sentences per turn. Two teammates will check your edit after you, so stop by tool call 35 at the latest.

## The issue

{problem_description}

## How to work

1. Find the code. Pick exact names from the issue: functions, classes, error messages, option names. Search for them with run_command, for example: grep -rn --include="*.py" "exact_name" . | head -30
2. Read only what you need. Files are long and read_file returns at most 150 lines, so always pass start_line and end_line around the line numbers grep gave you.
3. Edit early. Make your first edit_file call by tool call 12 at the latest, even if you are not fully certain. An edit you can improve is worth more than a perfect plan with no edit. Keep each edit small and never rewrite a whole file.
4. Test. Find the test file closest to the code you changed, for example: ls tests | grep -i name. Run that whole file, not a single test: python -m pytest tests/test_name.py -q --tb=short 2>&1 | tail -40. If no close test file exists, check the fix with a short python -c command.
5. Repair. If a failure comes from your change, fix it and run the file again. If a failure has nothing to do with your change, ignore it.
6. Finish. Run git diff to confirm the change is what you intended. Then stop calling tools and reply with exactly these three lines:
FILE: the source file you changed
CHANGE: one sentence saying what you changed
TEST: the test file you ran, or none

## Rules

- Change source code only. Changes to test files, conftest.py, pytest.ini, pyproject.toml, setup.cfg or tox.ini are thrown away.
- Put scratch files in /tmp, never in /workspace.
- Everything is already installed and there is no network, so never run pip.
- Never run the whole test suite. Always name one test file.
- Make one tool call at a time.
- If a tool response includes budget_warning, stop and write your three lines.
- Always leave a real edit behind. Never finish without changing source code.
"""

GATE_PROMPT = """\
You are the checker of a bug-fixing team working in the repository at /workspace. A teammate has just edited the source code. Your only job is to make sure the edit exists and did not break the code. You do not judge whether the fix is clever and you do not improve it. You cannot submit. Use at most 10 tool calls, one at a time.

## The issue

{problem_description}

## The teammate's note (may be empty)

{solve_note?}

## Report of an earlier checker (may be empty)

{gate_a_report?}

## Steps

1. Run this exact command:
git add -N . ; git diff --stat | tail -1; F=$(git diff --name-only | grep "[.]py$"); if [ -z "$(git diff --name-only)" ]; then echo NO_CHANGES; elif [ -z "$F" ]; then echo COMPILE_OK; else python -m py_compile $F && echo COMPILE_OK; fi

2. Read the answer and pick the first case that fits.

Case EMPTY: the answer says NO_CHANGES. Nothing was edited, even if the note says otherwise, because the teammate's edit failed. If the note names a FILE and a CHANGE, read the lines of that file where the change belongs. Otherwise search for exact names from the issue with grep -rn --include="*.py" "name" . | head -20 and read those lines. Make the smallest fix with one edit_file call, then run the command of step 1 again.

Case BROKEN: the answer has no COMPILE_OK. The error names a file and a line number. Call read_file on that file from 8 lines above to 8 lines below that line, and repair it with one small edit_file call. The usual causes are: a backslash followed by n or a quote typed inside the new code where a real new line or plain quote was meant; wrong indentation; a missing bracket, comma or colon. If the file is still broken after two repairs, run git checkout -- PATH and make the change described in the note again in one careful edit. Then run the command of step 1 again.

Case COMPILE_OK: go to step 3.

3. If the note names a TEST file, run:
timeout 60 python -m pytest TESTPATH -q --tb=short 2>&1 | tail -25
- If the output shows SyntaxError, IndentationError, ImportError, ModuleNotFoundError, NameError or an error during collection, and the traceback names a file that git diff lists, the edit broke the code: read the lines the traceback names, repair them with one small edit, and run the test command once more.
- Otherwise you are done. Tests that fail with an ordinary assertion are not your job: the test file will be replaced by a newer one. Do not edit anything because of them.

4. Stop calling tools and reply with one line: GATE OK, or GATE BROKEN followed by a short reason.

## Edit rules

- old_string is always required: one to three whole lines copied exactly from read_file, lines that appear only once in the file.
- In new_string, start a new line by really starting a new line. Never type a backslash followed by the letter n.
- If the tool says old_string matches several places, add the line above it to old_string, or set allow_multiple to true when every place needs the same change.
- If the tool says old_string was not found, read the lines again and copy just one line.
- Never send the same failing call twice.

## Rules

- Never edit test files or test configuration. Never create files in /workspace. Never run pip, git commit or git stash.
- Never undo a working edit. If step 1 says COMPILE_OK and step 3 shows no new loading error, change nothing.
- If a tool answer contains budget_warning, stop and write your one-line reply.
"""

FINALIZE_PROMPT = """\
The work is finished. Call the submit_patch tool now, with no arguments. Write nothing before the call. After the tool answers, reply with the single word DONE.
"""

# One entry per step. local_bench.py runs these in order; the YAML below says the same for Kaggle.
STAGES = [
    {"name": "solve", "prompt": "SOLVE_PROMPT", "history": True, "output_key": "solve_note",
     "tools": ["run_command", "read_file", "edit_file", "write_file", "get_status"],
     "temperature": 0.2, "seed": 42, "max_tokens": 4096, "think": True},
    {"name": "gate_a", "prompt": "GATE_PROMPT", "history": False, "output_key": "gate_a_report",
     "tools": ["run_command", "read_file", "edit_file"],
     "temperature": 0.2, "seed": 42, "max_tokens": 3072, "think": True},
    {"name": "gate_b", "prompt": "GATE_PROMPT", "history": False, "output_key": "gate_b_report",
     "tools": ["run_command", "read_file", "edit_file"],
     "temperature": 0.2, "seed": 7, "max_tokens": 3072, "think": True},
    {"name": "finalize", "prompt": "FINALIZE_PROMPT", "history": False, "output_key": "",
     "tools": ["submit_patch"],
     "temperature": 0.0, "seed": 42, "max_tokens": 128, "think": False},
]

ROOT_YAML = """\
name: bugfix_pipeline
agent_class: SequentialAgent
description: Fix the bug, check the edit twice, then submit.
sub_agents:
  - config_path: sub_agents/solve.yaml
  - config_path: sub_agents/gate_a.yaml
  - config_path: sub_agents/gate_b.yaml
  - config_path: sub_agents/finalize.yaml
"""

PROMPT_FILES = {"SOLVE_PROMPT": "solve.md", "GATE_PROMPT": "gate.md", "FINALIZE_PROMPT": "finalize.md"}


def stage_yaml(stage: dict) -> str:
    lines = [f"name: {stage['name']}", f"description: Step {stage['name']} of the bugfix pipeline.",
             f"model: {MODEL}", f"instruction: !include ../prompts/{PROMPT_FILES[stage['prompt']]}"]
    if not stage["history"]:
        lines.append("include_contents: none")
    lines.append("tools:")
    lines += [f"  - {tool}" for tool in stage["tools"]]
    if stage["output_key"]:
        lines.append(f"output_key: {stage['output_key']}")
    lines += ["generate_content_config:", f"  temperature: {stage['temperature']}"]
    if stage["temperature"]:
        lines.append("  top_p: 0.95")
    lines += [f"  seed: {stage['seed']}", f"  max_output_tokens: {stage['max_tokens']}", "  thinking_config:"]
    if stage["think"]:
        lines += [f"    thinking_budget: {stage['max_tokens'] // 2}", "    include_thoughts: true"]
    else:
        lines.append("    thinking_budget: 0")
    return "\n".join(lines) + "\n"


if __name__ == "__main__" or "get_ipython" in globals():
    if AGENT_DIR.exists():
        shutil.rmtree(AGENT_DIR)
    (AGENT_DIR / "prompts").mkdir(parents=True)
    (AGENT_DIR / "sub_agents").mkdir()
    (AGENT_DIR / "agent.yaml").write_text(ROOT_YAML, encoding="utf-8")
    (AGENT_DIR / "eval_config.yaml").write_text(EVAL_CONFIG_YAML, encoding="utf-8")
    for constant, filename in PROMPT_FILES.items():
        (AGENT_DIR / "prompts" / filename).write_text(globals()[constant], encoding="utf-8")
    for stage in STAGES:
        (AGENT_DIR / "sub_agents" / f"{stage['name']}.yaml").write_text(stage_yaml(stage), encoding="utf-8")
    zip_path = shutil.make_archive(str(WORK / "submission"), "zip", root_dir=AGENT_DIR)
    print(f"Agent written to {AGENT_DIR}\nCreated {zip_path}")
