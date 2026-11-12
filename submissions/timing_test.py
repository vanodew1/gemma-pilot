"""Build the wait-only timing test submission.zip.

Paste this file into one Kaggle notebook cell attached to the competition.
Each task should take about 2 minutes and the expected score is 0.00.
The notebook's total run time shows whether tasks run one at a time.
"""
import os
import shutil
from pathlib import Path

WORK = Path(os.environ.get("SUBMISSION_WORKDIR", "/kaggle/working"))
AGENT_DIR = WORK / "timing_test_agent"

AGENT_YAML = """\
name: timing_test_agent
model: gemma-4-e2b-it-qat-w4a16-ct
instruction: |
  Your only job is to wait. Follow these two steps exactly.
  Step 1: call the run_command tool once with the command: sleep 115
  Step 2: when it returns, call the submit_patch tool.
  Do not read, search, or change any files. Do nothing else.
tools:
  - run_command
  - submit_patch
generate_content_config:
  temperature: 0.0
  max_output_tokens: 256
  thinking_config:
    thinking_budget: 0
    include_thoughts: false
"""

EVAL_CONFIG_YAML = """\
evaluation:
  timeout_seconds: 120
  max_tool_calls: 5
  max_time_minutes: 2
  max_turns: 10
"""

if AGENT_DIR.exists():
    shutil.rmtree(AGENT_DIR)
AGENT_DIR.mkdir(parents=True)
(AGENT_DIR / "agent.yaml").write_text(AGENT_YAML, encoding="utf-8")
(AGENT_DIR / "eval_config.yaml").write_text(EVAL_CONFIG_YAML, encoding="utf-8")

zip_path = shutil.make_archive(str(WORK / "submission"), "zip", root_dir=AGENT_DIR)
shutil.rmtree(AGENT_DIR)
print(f"Created {zip_path}")
