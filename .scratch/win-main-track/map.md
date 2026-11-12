# Win the Gemma 4 main track

Label: wayfinder:map

## Destination

A written build spec that fixes the agent design, models for both final slots, per-task budgets, LoRA yes or no, and how we score locally, with nothing left to decide. Target date: 2026-11-13. Final submission deadline: 2026-12-02 23:59 UTC.

## Notes

Domain: Kaggle "Google - The Gemma 4 Developer Agent Competition". Terms are in `pilot/GLOSSARY.md`. Earlier decisions and verified rules are in `pilot/agents/PROJECT-BRIEF.md`.

Skills for every session: `grilling` and `domain-modeling` for grilling tickets; `research` for research tickets.

Settled while charting (2026-11-09):

- Win means the highest main leaderboard score from the main slot, plus the small-model bonus from the small-model slot.
- Course work comes first. All other time goes to the main track.
- Team is the user and Areesha Ashfaq, both able to submit on Kaggle.
- Only official competition rules, models and data, including for any training. Anything external comes back to the user as a question.
- One whole dev repo stays sealed, used only to judge candidates before sending them to Kaggle.
- Route (2026-11-10): small-model slot gets most of the time, then the same agent moves to 31B around 2026-11-21 for the main slot. Test whether a LoRA loads on the QAT model by 2026-11-14.
- The first submission is the real E4B agent v1; the user skipped the wait-only test (2026-11-10). Plan on tasks running one at a time until a run shows otherwise.
- Start from a single agent with a short prompt; the official sample is only a format example. One change per submission, logging every score.
- Every submission is budgeted to finish within 10 hours at worst, because going over 12 hours scores zero.

Standing preferences: plain words. Numbered grilling questions with a recommended answer, worded so "yes" accepts it. The user and partner write report prose themselves. Push only as GitHub account `vanodew1`, with no Claude attribution.

## Decisions so far

- [What in the harness moves the score most?](issues/01-harness-levers.md): budgets that fit 12 hours come first, then 31B for the main slot, whole-test-file checks, line-range localization and early edits; the harness itself isn't available to run locally yet.
- [Can we get the harness to run ourselves?](issues/09-get-the-harness.md): yes, from the official wheelhouse dataset inside a Kaggle notebook; running it at home is untested.
- [Which dev repo stays sealed?](issues/03-sealed-repo.md): `rich`, used only for final checks.

## Not yet specified

- Course due dates: the written report and peer evaluation are still due; the user set dates aside for now (2026-11-09).
- Order of changes across roughly 15 to 20 leaderboard attempts, once the agent design and timing are known.
- Work split between the two team members (postponed earlier).
- If LoRA is a yes: how to build traces from the unsealed dev tasks, and where training runs.
- The cut-off date for freezing both final slots.

## Out of scope

- Paper track: closes 2026-11-12 and the pilot was never rebuilt on competition tasks; effort goes to the main track instead.
- Outside benchmarks such as SWE-bench: excluded by the competition-only rule.
- `design/ground-then-choose` as a base: kept as a source of ideas only, since we build up from the official sample.
