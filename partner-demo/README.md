# Mini Developer Agent Demo (CS 351)

A tiny version of our Gemma 4 Developer Agent idea, running on a toy repo.

- `demoRepo/` is a small shop project with a planted bug (discount codes are calculated wrong). `ISSUE.md` is the bug report. 3 of 7 tests fail at the start.
- `agent.py` is the agent. Gemma reads the issue, uses tools, edits the code, and the tests decide if it's fixed.

Four modes, same as the plan in our proposal:

| Mode | Search tool (A) | Test-and-retry (B) |
| --- | --- | --- |
| baseline | no | no |
| search | yes | no |
| retry | no | yes (up to 3 attempts) |
| both | yes | yes |

Every run starts from a fresh copy of the repo, so you can run it again and again.

## Setup (do this tonight, not in class)

1. Install Python packages: `pip install requests pytest`
2. Install Ollama from https://ollama.com and start it (`ollama serve`, or just open the app).
3. Download Gemma 4 12B. Check the exact tag on https://ollama.com/library/gemma4 (it should look like `gemma4:12b`), then: `ollama pull gemma4:12b`
4. Test it: `python agent.py --mode both`

The 12B model needs about 16 GB of RAM/VRAM. If your laptop struggles, use `gemma4:e4b` instead with `--model gemma4:e4b` (smaller, weaker, faster).

## Running the demo

```
python agent.py --mode baseline
python agent.py --mode both
python agent.py --mode all        # all four, then a comparison table
```

Other options: `--model <ollama tag>`, `--url <any OpenAI-compatible endpoint>`.

## Backup plan if the model is slow or breaks live

Every live run saves the model's replies in `runs/<mode>_log.json`. Replay a saved run with:

```
python agent.py --mode both --replay
```

The tools and tests still really run, only the model replies come from the recording. Do a good live run tonight for each mode so you have recordings, and tell the professor if you switch to replay.

## What to point out in the demo

- **Search (A):** with search, the agent jumps straight to `shop/coupons.py`. Without it, it has to list and open files one by one.
- **Retry (B):** if the first fix is wrong, the failing test output goes back to the model and it tries again. Watch for the `[retry]` line.
- **Result line:** steps, tool calls and attempts. These are the same kinds of numbers we'll compare on the real competition bugs.

Note: Ollama's Gemma 4 12B is the same model family as the competition's `gemma-4-12b-it-qat-w4a16-ct`, just packaged differently for laptops. On the real competition we'll use the official harness.
