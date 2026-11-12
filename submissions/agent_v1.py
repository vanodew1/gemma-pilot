"""Agent v1 for the Gemma 4 Developer Agent Competition.

To test on dev tasks: paste into a new cell right after section 2 of a copy of
the official Getting Started notebook, then follow the run steps.
To submit only: paste alone into one notebook cell and run it.
Either way it writes the agent and /kaggle/working/submission.zip.
"""
import os
import random
import shutil
from pathlib import Path

MODEL = "gemma-4-e4b-it-qat-w4a16-ct"
WORK = Path(os.environ.get("SUBMISSION_WORKDIR", "/kaggle/working"))
AGENT_DIR = WORK / "sample_submission"

AGENT_YAML = f"""\
name: swe_agent_v1
model: {MODEL}
instruction: !include prompts/system.md
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
generate_content_config:
  temperature: 0.2
  top_p: 0.95
  seed: 42
  max_output_tokens: 4096
  thinking_config:
    thinking_budget: 2048
    include_thoughts: true
"""

EVAL_CONFIG_YAML = """\
evaluation:
  timeout_seconds: 120
  max_tool_calls: 40
  max_time_minutes: 4.5
  max_turns: 80
"""

SYSTEM_PROMPT = """\
You are fixing one issue in the repository at /workspace. You have about 4 minutes, so act quickly and keep your reasoning to a few sentences per turn.

## The issue

{problem_description}

## How to work

1. Find the code. Pick exact names from the issue: functions, classes, error messages, option names. Search for them with run_command, for example: grep -rn --include="*.py" "exact_name" . | head -30
2. Read only what you need. Files are long and read_file returns at most 150 lines, so always pass start_line and end_line around the line numbers grep gave you.
3. Edit early. Make your first edit_file call by tool call 12 at the latest, even if you are not fully certain. An edit you can improve is worth more than a perfect plan with no edit. Keep each edit small and never rewrite a whole file.
4. Test. Find the test file closest to the code you changed, for example: ls tests | grep -i name. Run that whole file, not a single test: python -m pytest tests/test_name.py -q --tb=short 2>&1 | tail -40. If no close test file exists, check the fix with a short python -c command.
5. Repair. If a failure comes from your change, fix it and run the file again. If a failure has nothing to do with your change, ignore it.
6. Finish. Run git diff to confirm the change is what you intended, then call submit_patch as your last action.

## Rules

- Change source code only. Changes to test files, conftest.py, pytest.ini, pyproject.toml, setup.cfg or tox.ini are thrown away.
- Put scratch files in /tmp, never in /workspace.
- Everything is already installed and there is no network, so never run pip.
- Never run the whole test suite. Always name one test file.
- Make one tool call at a time.
- If a tool response includes budget_warning, stop exploring and call submit_patch.
- Always leave a real edit behind. Never finish without changing source code.
"""

if AGENT_DIR.exists():
    shutil.rmtree(AGENT_DIR)
(AGENT_DIR / "prompts").mkdir(parents=True)
(AGENT_DIR / "agent.yaml").write_text(AGENT_YAML, encoding="utf-8")
(AGENT_DIR / "eval_config.yaml").write_text(EVAL_CONFIG_YAML, encoding="utf-8")
(AGENT_DIR / "prompts" / "system.md").write_text(SYSTEM_PROMPT, encoding="utf-8")

zip_path = shutil.make_archive(str(WORK / "submission"), "zip", root_dir=AGENT_DIR)
print(f"Agent written to {AGENT_DIR}\nCreated {zip_path}")

# Fixed comparison set. The rich repo stays sealed for final checks.
if "tasks" in globals():
    rng = random.Random(20261110)
    fastapi = sorted(
        (t for t in tasks if t.repo == "fastapi/fastapi"), key=lambda t: t.instance_id
    )
    others = sorted(
        (t for t in tasks if t.repo in ("psf/requests", "encode/httpx")),
        key=lambda t: t.instance_id,
    )
    EVAL_TASKS = rng.sample(fastapi, 26) + others
    rng.shuffle(EVAL_TASKS)
    print(f"EVAL_TASKS: {len(EVAL_TASKS)} tasks, none from rich")
