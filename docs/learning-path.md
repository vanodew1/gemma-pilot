# Learning Path — Understanding the Gemma Distillation Agent, End to End

**Goal:** Be able to explain the *whole* mechanism out loud to the prof — the grading
loop (outside) **and** the model + training that powers it (inside) — deeply, without notes.

**The competition:** [Google – The Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/747519)
— a SWE-bench-style coding-agent benchmark. Your diagram is exactly its grading loop.

**How to use this:** One rung at a time. Each rung ends with a small **explainer**
(a diagram or worked example) you can literally hand the prof as evidence.

**How to study each rung** (easy → hard — you rarely need all three):
- 🎥 **Video** first — builds the gut feeling.
- 📖 **Blog/book** next — fills the gaps at your own pace.
- 📄 **Paper** last, *optional* — this is the "deep" flex that impresses the prof. Skim, don't grind.

**One book that covers rungs 2–5** (if you prefer a book spine):
*"Hands-On Large Language Models"* by Jay Alammar & Maarten Grootendorst (O'Reilly, 2024).
Visual, plain-language, covers transformers → fine-tuning → distillation. Alammar also wrote
the famous "Illustrated Transformer" blog below, so the style matches.

---

## The map

```
    YOU ARE HERE
   ┌──────────────┐
   │  outer loop  │  Rung 0 — your diagram (grading harness)        ✅ solid
   └──────┬───────┘
          │ zoom in
   ┌──────▼───────┐
   │ 1. agent =   │  the "robot" is a model emitting tool calls in a loop
   │    a model   │
   ├──────────────┤
   │ 2. inside    │  tokens + attention — how it "reads" a bug report
   │    the model │
   ├──────────────┤
   │ 3. small vs  │  why E4B is worse than 12B, why you still use E4B
   │    big       │
   ├──────────────┤
   │ 4. LoRA      │  cheap fine-tuning that fits your 16GB card
   ├──────────────┤
   │ 5. distill   │  12B teacher teaches E4B student   ← your actual project work
   ├──────────────┤
   │ 6. full      │  trained E4B → runs your diagram → score. circle closed.
   │    circle    │
   ├──────────────┤
   │ 7. self-     │  (bonus/frontier) make the agent verify & improve itself
   │   improving  │
   └──────────────┘
```

---

## Rung 0 — The outer loop (already done ✅)

This is your hand-drawn diagram. Keep it; everything else hangs on it.
Real GitHub bug + PR → Kaggle hides the fix and the tests → agent gets broken repo + bug
report → agent loops (read, grep, edit, test, retry) → submits a diff → fresh repo applies it →
**hidden** tests → score.

**Study it with:**
- 📄 [SWE-bench: Can LLMs Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)
  — the benchmark your competition copies. Read the intro + the figure of the pipeline; that *is*
  your diagram, written up by researchers. (Fun fact from it: even GPT-4 solved only a few % of
  these — which is *why* training a good agent is a real project.)

---

## Rung 1 — "Our agent" is a model emitting tool calls in a loop

**Idea:** The agent is a language model. Text in → text out. Some of that text is a *command*
("grep for `parse_date`"). The harness runs it, pastes the result back as more text, and the
model writes its next step. Repeat = the **agent loop**.

**Explainer you make:** Redraw step ③ as a loop: `model writes thought + one action → harness
runs action → result pasted back → model writes next action`, until it writes `submit_patch`.

**Study it with:**
- 🎥 [Andrej Karpathy — "[1hr Talk] Intro to Large Language Models"](https://www.youtube.com/@AndrejKarpathy)
  (search the exact title on his channel, ~1 hr). No math. Gives you "a model is a next-word
  predictor you can fine-tune" — the foundation of this whole rung.
- 🎥 Stanford **CS329A: Self-Improving AI Agents** (20 lectures, Autumn 2025) —
  [course site](https://cs329a.stanford.edu/) · [YouTube playlist](https://www.youtube.com/playlist?list=PL3058ht9NqT1NG6Y663elpHSDh-AW1TIr).
  For Rung 1, watch **#1 Course Overview** and **#5 Multi-step Reasoning / Planning**.
  (Self-improvement lectures → Rung 7. Full 20-lecture table in the Appendix.)
- 🎥 Stanford **CS329Z: Engineering AI Agents** (Fall 2026) — [course site](https://cs329z.stanford.edu/).
  The hands-on "how an agent is actually built" view. For Rung 1, watch **#1 What Are Agentic
  Systems?**, **#4 Tool Use & Function Calling** (the exact core of this rung), and **#6 Agent Design
  Patterns & Scaffolds**. Straight at your competition: **#16 Guest — SWE-bench authors** and
  **#18 Coding & Software Agents**. (Full table in the Appendix.)
- 📄 [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
  (project page: [react-lm.github.io](https://react-lm.github.io)) — the paper that named the
  "think → act → observe → repeat" loop your agent runs. Read §1–2 only.
- 🔎 **Best exercise:** open one real transcript from your home harness and mark, line by line,
  which text the *model* wrote vs. which the *harness* pasted back. That split is the whole idea.

---

## Rung 2 — Inside the model: tokens and attention (just enough)

**Idea:** Text → **tokens** → vectors (**embeddings**). **Attention** lets each token look at the
others, so "error in `parse_date`" connects to the function seen earlier. Output = probability of
the next token. Loop = generation. You need the *mechanism*, not the math.

**Explainer you make:** Take one sentence from a real bug report, show it split into tokens, draw
arrows for which tokens "attend to" the error name. One picture.

**Study it with:**
- 🎥 [3Blue1Brown — "Attention in transformers, step-by-step" (Ch. 6)](https://www.3blue1brown.com/lessons/attention)
  and its Ch. 5 "Transformers, the tech behind LLMs" (same site). The single best visual
  explanation that exists. Watch both (~45 min total).
- 📖 [Jay Alammar — "The Illustrated Transformer"](https://jalammar.github.io/illustrated-transformer/)
  — the classic picture-by-picture blog. Read after the videos to lock it in.
- 📄 *(optional, hard)* [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — the original
  transformer paper. Skim Fig. 1 and §3.2; don't grind the equations.

---

## Rung 3 — Small vs big: E4B vs 12B

**Idea:** Bigger models (12B params) reason better but are heavy. The small model (E4B) is weaker
but fits the competition's limits and your RTX 5070 Ti (16 GB). The project exists to make the
*small* model punch above its weight.

**Explainer you make:** A two-column card — 12B teacher vs E4B student: size, speed, memory,
smarts, and which one the competition actually scores.

**Study it with:**
- 📄 [Gemma 3 Technical Report](https://arxiv.org/abs/2503.19786) (Google DeepMind) — the official
  source for your exact models. Read the model-sizes table and the training section. **Key line:**
  *"All Gemma models are trained with knowledge distillation"* — i.e. your project is how Google
  itself builds these.
- 📖 [Gemma model card / docs](https://ai.google.dev/gemma/docs) — plain spec of sizes & context.
- 📏 Pin the exact allowed sizes + compute budget from the **official competition rules page**
  (competition-only scope: use the official Gemma comp materials for anything touching the real pipeline).

---

## Rung 4 — LoRA: cheap fine-tuning that fits 16 GB

**Idea:** Fine-tuning = nudging weights to be better at one task. Retraining all of E4B won't fit
in 16 GB. **LoRA** freezes the big model and trains tiny add-on matrices (**adapters**) — far fewer
numbers, so it fits. **QLoRA** adds 4-bit compression so it fits even easier.

**Explainer you make:** The "frozen big weight matrix + small trainable adapter beside it" picture,
with how many numbers each holds.

**Study it with:**
- 📄 [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685) — read the
  abstract + Fig. 1. The whole idea is one picture.
- 📄 [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314) — why you can
  fine-tune on a single small GPU (directly relevant to your 16 GB card).
- 📖 [Hugging Face PEFT docs](https://huggingface.co/docs/peft) — the practical "how you actually run
  LoRA" guide. Maps straight onto your approved plan (train an E4B adapter).

---

## Rung 5 — Distillation: the 12B teacher teaches the E4B student ← your actual work

**Idea:** Run the smart **12B teacher** on the bug tasks; it produces good answers/traces. Train the
**E4B student** (via LoRA) to imitate it. Learning from a smart teacher's outputs beats learning from
raw data — the teacher's answers are richer signal. This is **knowledge distillation**, the core of
your project.

**Explainer you make:** A flow — `12B teacher solves tasks → collect its outputs → LoRA-train E4B to
match → held-out screen-set test`. Mark which arrow is the "distillation."

**Study it with:**
- 📄 [Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531) (Hinton, Vinyals,
  Dean, 2015) — the paper that invented the idea. Short. The key concept: "soft targets" — the teacher
  hands over *how sure it was about every option*, not just the final answer, and that's the rich signal.
- 🔗 Tie it back to the [Gemma 3 report](https://arxiv.org/abs/2503.19786): it's a real, modern,
  large-scale example of the exact teacher→student setup you're doing.
- 🔎 Map your *own* approved plan (12B teacher runs → train E4B adapter → screen set held out) onto the
  flow above. That mapping *is* the understanding.

---

## Rung 6 — Close the circle: training meets grading

**Idea:** Snap the halves together. The trained E4B student becomes the "our agent" box in your original
diagram. It runs the eval loop (Rung 0), hidden tests run, you get a Kaggle score. Training exists only
to raise that score.

**Explainer you make (capstone):** One master diagram = your original outer loop **with the inside of
the "agent" box filled in** (model + LoRA + distillation). If you can draw this from memory and narrate
it, you've hit the prof's bar.

**Study it with:** No new sources — this is synthesis. Assemble it from rungs 0–5.

---

## Rung 7 — Self-improving agents (bonus / frontier)

**Idea:** An agent gets better by *checking its own work and retrying* — and, further out, by
generating its own good attempts and training on them. Your diagram already has a baby version:
step ③'s "run nearby tests → fix again if broken" is the agent verifying and correcting itself.
This rung makes that loop *smart*: better verification, smarter retry, and spending more compute
at answer-time ("test-time compute").

**Explainer you make:** Circle the "run tests → fix if broken" part of your diagram and annotate
the upgrade — *what* to verify, *when* to retry, *when* to stop.

**Study it with:**
- 🎥 Stanford **CS329A: Self-Improving AI Agents** — [course site](https://cs329a.stanford.edu/) ·
  [YouTube playlist](https://www.youtube.com/playlist?list=PL3058ht9NqT1NG6Y663elpHSDh-AW1TIr).
  The self-improvement core: **#2 Test-time Compute Scaling**, **#3 Robust Verification**,
  **#4 Learning from Feedback with Tools/Code**, **#6 Train-Time Scaling / Scaling RL**,
  **#7 Open-Ended Evolution of Self-Improving Agents**, **#8 Self-Improvement with Search & Deep
  Research**. Straight at your competition: **#13 Agentic Frameworks for Software Engineering** and
  **#17 Agentic Evaluations & Long-Horizon Tasks**. **Watch AFTER rungs 1–5** — they assume the basics.

**Why it's here:**
- 🏆 **Competition:** Smarter self-verification + retry = a direct lever on your leaderboard score —
  more correct patches out of the *same* E4B model, just at inference time.
- 🔗 **Ties to Rung 5:** "Self-improvement" (agent makes its own good traces → trains on them) is a
  cousin of teacher→student distillation. Connecting the two = serious depth.
- 📚 **Prof flex:** Frontier awareness (verification, reward hacking, test-time scaling) goes beyond
  the required mechanism — extra-credit territory.

---

## Words that'll come up (quick glossary)

- **Token** — a chunk of text the model reads/writes (roughly a word-piece).
- **Attention** — mechanism letting each token pull in the other tokens that matter to it.
- **Parameters / weights** — the numbers inside the model; "4B" = ~4 billion of them.
- **Fine-tuning** — adjusting a model's weights to be better at one task.
- **LoRA / QLoRA** — fine-tuning tiny add-on adapters while freezing (and compressing) the big model.
- **Adapter** — the small trainable matrices LoRA adds.
- **Teacher / student** — big model that demonstrates (12B) / small model that imitates (E4B).
- **Soft targets** — the teacher's full confidence over all options; the rich signal distillation copies.
- **Knowledge distillation** — training the student to copy the teacher.
- **Agent loop (ReAct)** — model writes action → harness runs it → result fed back → repeat.
- **Harness** — the competition code that runs the agent and grades the patch.
- **Held-out / screen set** — tasks kept aside to honestly test improvement.
- **Test-time compute** — extra compute spent *while answering* (retry, self-check) to do better.
- **Verification** — the agent checking its own output before submitting (e.g., running tests).
- **Self-improving agent** — one that improves by verifying/retrying, or by training on its own good attempts.

---

## How we'll work

One rung per sitting. For each: you watch/read the resource → I teach it plainly & answer your
questions → we build its explainer → you check it off → next rung. Start = **Rung 1**.

- [ ] Rung 1 — agent = model in a loop
- [ ] Rung 2 — tokens + attention
- [ ] Rung 3 — small vs big
- [ ] Rung 4 — LoRA
- [ ] Rung 5 — distillation (your work)
- [ ] Rung 6 — full circle (capstone)
- [ ] Rung 7 — self-improving agents (bonus/frontier)

---

## Appendix — Stanford course lecture lists (full)

Legend: ⭐ = highest value for you · 🏆 = directly about your competition (software-engineering agents).

### CS329A: Self-Improving AI Agents — 20 lectures (Autumn 2025)

[course site](https://cs329a.stanford.edu/) · [YouTube playlist](https://www.youtube.com/playlist?list=PL3058ht9NqT1NG6Y663elpHSDh-AW1TIr)
· Instructors: Aakanksha Chowdhery, Azalia Mirhoseini.
*(Playlist is titled "Winter 2025"; the course site says Autumn 2025. The presentation sessions
may not all be uploaded to YouTube.)*

| # | Lecture | Maps to |
|---|---------|---------|
| 1 | Course Overview | Rung 1 |
| 2 | Test-time Compute Scaling | Rung 7 ⭐ |
| 3 | Robust Verification | Rung 7 ⭐ |
| 4 | Learning from Feedback with Tools/Code | Rung 7 ⭐ |
| 5 | Multi-step Reasoning / Planning | Rung 1 |
| 6 | Train-Time Scaling / Scaling RL | Rung 7 |
| 7 | Open-Ended Evolution of Self-Improving Agents | Rung 7 ⭐ |
| 8 | Self-Improvement with Search & Deep Research Agents | Rung 7 ⭐ |
| 9 | Guest — Melvin Johnson (DeepMind): Post-training, Chatbots→Agents | optional |
| 10–12 | Mid-term presentations | skip |
| 13 | Agentic Frameworks for Software Engineering | 🏆 ⭐ |
| 14 | Augmenting Agents with Memory | optional |
| 15 | Guest — Denny Zhou (DeepMind): LLM Reasoning | optional |
| 16 | Guest — Thang Luong (DeepMind): Superhuman Reasoning (AlphaProof / Gemini IMO) | optional |
| 17 | Agentic Evaluations & Long-Horizon Tasks | 🏆 |
| 18 | Guest — Misha Laskin (Reflection AI): Agentic Systems for Autonomy | optional |
| 19 | Guest — Danny Driess (Physical Intelligence): Agents in Robotics | skip (robotics) |
| 20 | Future Research Areas | optional |

### CS329Z: Engineering AI Agents — ~19 sessions + demo day (Fall 2026)

[course site](https://cs329z.stanford.edu/) · Instructors: Diyi Yang, Michael Ryan, John Yang.
No single playlist — each lecture links its own video. *Course is ongoing; videos exist through
~#10, later ones post as the term continues.*

| # | Lecture | Video | Maps to |
|---|---------|-------|---------|
| 1 | Foundations & Landscape — What Are Agentic Systems? | [▶](https://youtu.be/DGI4vucR71w) | Rung 1 |
| 2 | LLMs for Builders | [▶](https://youtu.be/Vr1NzH8bT44) | Rung 1/2 |
| 3 | Building Blocks — Retrieval-Augmented Generation (RAG) | [▶](https://youtu.be/psLc-46GqY0) | optional |
| 4 | Tool Use & Function Calling | [▶](https://youtu.be/s0S38lz6O7M) | Rung 1 ⭐ |
| 5 | Frameworks & Agent Design | [▶](https://youtu.be/q0Q-Hy8TTps) | Rung 1 |
| 6 | Agent Design Patterns & Scaffolds | [▶](https://youtu.be/JC_pLC5EX_w) | Rung 1 ⭐ |
| 7 | Memory & Multi-Agent Systems | [▶](https://youtu.be/qh5tP6PBZ6U) | optional |
| 8 | Multi-Agent Systems | [▶](https://youtu.be/TlX_ft_PQIM) | optional |
| 9 | Optimization | [▶](https://youtu.be/e_m99aR7_3Q) | Rung 4/7 |
| 10 | Guest — Terminal-Bench | [▶](https://youtu.be/7GW-9ug2nvw) | optional |
| 11 | Data for Agentic Systems | — | Rung 5 |
| 12 | Data Selection & Quality | — | Rung 5 |
| 13 | Evaluation for Agentic Systems | — | 🏆 |
| 14 | Fireside Chat — Andrew Ng | — | optional |
| 15 | LLM-as-Judge & Evaluation Infrastructure | — | 🏆 |
| 16 | Guest — SWE-bench (Jimenez & Wettig) | — | 🏆 ⭐ |
| 17 | Safety & Guardrails | — | optional |
| 18 | Coding & Software Agents | — | 🏆 ⭐ |
| 19 | Personal Agents | — | optional |
| — | Open Problems & Final Demos (Demo Day) | — | — |
