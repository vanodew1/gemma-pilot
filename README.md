# Gemma 4 coding agent (Group 9)

CS/CE 351/363 AI, Fall 2026. Syed Ibad Asim and Areesha Ashfaq.

We're improving a Gemma 4 coding agent for Kaggle's "Gemma 4 Developer Agent" competition (main track due Dec 2) and writing a paper for its Paper Track (due Nov 12).

The agent: read the bug report → **(A)** search the code for the file to fix → edit a fix → **(B)** run the tests and retry on failure (at most 3 tries).

| Where | What |
|---|---|
| `docs/DECISIONS.md` | What's decided, what's open, what's next |
| `docs/COMPETITION.md` | Competition rules, deadlines, limits, data and the course rubric |
| `GLOSSARY.md` | What our terms mean |
| `pilot/` | Keyword-search pilot for step (A): Gemma-picked search words put the right file first 80% of the time vs 58% for BM25 (55 old issues). See `pilot/README.md` |
| `partner-demo/` | Toy agent with search and retry modes |
