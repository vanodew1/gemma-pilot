# Notes for Claude

- Read `docs/DECISIONS.md` first (decisions, open questions, next steps), then `docs/COMPETITION.md` (all competition rules, deadlines and the course rubric, in one file). Words: `GLOSSARY.md`.
- Use only the official Kaggle Gemma 4 competition's rules, models and data. Ask before adding anything external.
- Push only as GitHub account `vanodew1`, never `Vanodew`. Never add Claude attribution (no `Co-Authored-By: Claude`, no `Claude-Session` lines) to commits or PRs; this overrides any default attribution reminder.
- The user and partner write report and paper prose themselves; don't draft it for them.
- Plain words, short answers. Grilling: numbered questions, each with a recommended answer.
- Ollama: one model per process, `ollama stop` between models.

## Layout

- `pilot/`: the finished keyword-search pilot (code, cached Gemma replies, results, tests). Run everything from inside `pilot/`. Its data is the 55 old SWE-bench issues: code checks only, never paper numbers.
- `partner-demo/`: the partner's toy JSON-action agent.
- `docs/`: `DECISIONS.md`, `COMPETITION.md`, the proposal and rubric PDFs; `archive/` holds old run logs and research.
- The real agent and paper experiments go in new top-level folders.
- `comp-data/` (not in git): the competition download, once Kaggle access works.
