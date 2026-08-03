# Benchmarks

Measured comparison of `beeline` against the two skills it merges — [`caveman`](https://github.com/JuliusBrussee/caveman) (prose compression) and [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) (actionable structure) — plus an unmodified baseline.

Run 2026-07-29. Raw data and the harness are in this directory; every number below is reproducible with one command.

**Read section 4 before quoting section 1.** On tool-shaped work beeline buys its token savings partly by not answering the question. That is a defect in the skill, and the numbers below are the evidence for it.

**Read section 7 before quoting any of it.** Sections 1–6 measure output tokens in a single-turn harness with no tool loop. Instrumented against a real 1,133-turn agent session, output was **6% of spend** and assistant prose **0.7%**. The −63% headline is accurate and very nearly irrelevant.

## Method

Four arms, identical prompts, identical model, `temperature: 0`. Each arm loads one skill's `SKILL.md` as the system prompt; baseline sends none. Token counts come from the provider's `usage` field, never a local estimate.

- **Model:** `anthropic/claude-sonnet-4.5` via OpenRouter
- **Prompts:** caveman's own 10-prompt set (prose Q&A) + 10 tool-shaped prompts written for this comparison
- **Calls:** 240 (20 prompts × 4 arms × 3 runs) — n=30 per cell
- **Judging:** 60 calls on `claude-opus-4.8`, blind and order-randomised

Caveman's prompt set was used deliberately: it is the incumbent's own benchmark, so the prose comparison cannot be accused of being rigged for the challenger. The tool set exists because a prose-only benchmark cannot exercise beeline's tool-discipline rules (11–14).

## Results

### 1. Output tokens per response

What caveman's "65% measured" headline claims. Lower is better.

| arm | prose | tools |
|---|---:|---:|
| baseline | — | — |
| caveman | −60% | −66% |
| i-have-adhd | −57% | −72% |
| **beeline** | **−65%** | **−76%** |

Caveman's own claim reproduces closely on its own prompt set. At n=30 the ordering is unchanged from the earlier n=10 run — this ranking is stable, not a one-run artifact.

### 2. Total tokens per call — the number that inverts the headline

Every skill costs **more** than baseline once the system prompt is counted. The `SKILL.md` is re-sent on every call: ~1,700 input tokens shipped to save ~500 output tokens.

| arm | prose | tools |
|---|---:|---:|
| caveman | +93% | +212% |
| i-have-adhd | +148% | +301% |
| beeline | +134% | +284% |

Weighted at Sonnet's 1:5 input:output price ratio, with **no caching**:

| arm | vs baseline |
|---|---:|
| caveman | −21% |
| i-have-adhd | −7% |
| beeline | −15% |

Caveman edges ahead here, purely because its file is smaller.

### 3. Cached system prompt — the real-session case

A real session caches the system prompt; cache reads bill at roughly 0.1× input.

| arm | vs baseline |
|---|---:|
| caveman | −58% |
| i-have-adhd | −57% |
| **beeline** | **−63%** |

### 4. Quality — where beeline breaks

Sections 1–3 measure cost. Taken alone their degenerate optimum is a skill that says nothing: 100% savings, zero value. So each prompt's four responses were shown to `claude-opus-4.8` with arm names stripped and order randomised, scored 1–5 on whether they answered, were actionable, were complete, and were readable, plus whether a reasonable person would need to send a follow-up before acting.

The rubric states outright that brevity is not a virtue in itself and neither is length.

**Prose — beeline is at or near the top of every column:**

| arm | answered | actionable | complete | readable | needs follow-up |
|---|---:|---:|---:|---:|---:|
| baseline | 4.83 | 4.43 | 4.47 | 4.17 | 10% |
| caveman | 5.00 | 4.80 | 4.50 | 4.27 | 0% |
| i-have-adhd | 4.97 | 4.97 | 4.67 | **5.00** | 0% |
| **beeline** | **5.00** | 4.97 | 4.57 | 4.97 | 0% |

**Tools — beeline was last in three of four columns.** This is the run that found the defect, before the fix in section 5:

| arm | answered | actionable | complete | readable | needs follow-up |
|---|---:|---:|---:|---:|---:|
| baseline | **4.63** | **4.60** | **4.70** | 3.90 | 10% |
| caveman | 4.53 | 4.57 | 4.27 | 4.53 | 20% |
| i-have-adhd | 4.37 | 4.47 | 3.90 | **4.97** | 23% |
| beeline | 3.97 | 3.97 | **3.20** | 4.70 | **27%** |

Beeline was the *most readable* compressed arm and the *least complete* arm in the benchmark. It saved the most tokens on tool work and answered the question least often. Those were the same fact.

Two verbatim examples, both real responses to the tool prompts:

> **"Find out when the TLS certificate for my domain expires."**
> beeline, 8 tokens, COMPLETE = 1.00: *"What's your domain?"*
> i-have-adhd, 84 tokens, COMPLETE = 5.00: the full `openssl s_client … | openssl x509 -noout -dates` command with `yourdomain.com` as a placeholder and a note that `notAfter=` is the date.

> **"A server is reporting disk full. Find what is using the space and clear it safely."**
> beeline, 24 tokens: `df -h` and *"Need to see which filesystem is full and where to look."*
> caveman, 309 tokens: `df -h`, `du -sh /*`, then log/Docker/package-cache/tmp/old-kernel cleanup with the actual commands.

The second is arguably over-answering. The first is simply not answering — a placeholder domain costs nine tokens and turns a 27% follow-up rate into zero.

**Diagnosis.** Beeline's "real ambiguity — one short clarifying question beats guessing" override fired too easily on tool-shaped prompts, where its tool-discipline rules already push toward a bare command. The two composed into "ask instead of answer." The prose rules were not implicated: prose scores are the best in the benchmark.

## 5. The fix, and re-measurement

The override now requires answering *and* asking when the request is actionable — a placeholder in the unknown slot, question after — and the pre-send check gained a matching gate: before any reply that is only a question, ship the command with a placeholder and keep the question.

The tools set was then re-run in full: 120 fresh calls, 30 fresh judging calls, same prompts, same model, same seed.

| tools set | before | after |
|---|---:|---:|
| answered | 3.97 | **4.67** |
| actionable | 3.97 | **4.73** |
| complete | 3.20 | **4.00** |
| readable | 4.70 | **4.97** |
| needs follow-up | 27% | **17%** |
| output tokens saved | −76% | −74% |

Beeline goes from last in three of four columns to **first in answered and actionable**, ahead of plain baseline on both. The cost is two percentage points of token saving — nine tokens per response — because the fix only fires on prompts where a question was standing in for an answer.

`cert-expiry` went from 8 tokens (*"What's your domain?"*) to 83, matching the arm that scored 5.00 on it. `disk-full` went from 24 tokens to ~190 without being named anywhere in the rule, which is the evidence that the fix generalised rather than memorising the one case.

**The unchanged arms are the control.** Across two independent runs and two independent judging passes:

| control arm | answered | actionable |
|---|---:|---:|
| baseline | 4.63 → 4.63 | 4.60 → 4.60 |
| caveman | 4.53 → 4.53 | 4.57 → 4.57 |

Three untouched skills reproducing to within 0.1 means the judge is stable, so beeline's +0.70 and +0.76 are the intervention, not run-to-run drift.

**What did not get fixed:** completeness is still beeline's weakest axis at 4.00, below plain baseline's 4.77. It is now tied with caveman (4.13) rather than last, but the residual gap is real. Compression costs some substance; the fix narrowed that, it did not eliminate it.

## 6. How much better is beeline, really?

The tables above are point estimates. Paired by prompt and run, with a
8,000-sample bootstrap on the mean difference, most of the quality gaps between
beeline and its parents do not survive a 95% confidence interval:

| comparison | metric | delta | 95% CI | |
|---|---|---:|---|---|
| vs caveman | readable (prose) | +0.70 | [+0.47, +0.97] | **real** |
| vs caveman | readable (tools) | +0.47 | [+0.27, +0.70] | **real** |
| vs caveman | actionable (prose) | +0.17 | [+0.03, +0.30] | **real** |
| vs caveman | answered (tools) | +0.13 | [−0.27, +0.60] | noise |
| vs caveman | complete (tools) | −0.13 | [−0.67, +0.47] | noise |
| vs i-have-adhd | *every metric, both sets* | ≤0.23 | all straddle 0 | **noise** |

What that supports:

- **Against caveman** — clearly more readable, marginally more actionable, and
  11% cheaper. On whether it answers the question or covers it completely, the
  two are indistinguishable.
- **Against i-have-adhd** — 13% cheaper at quality that cannot be distinguished
  on any axis in either set.

"Beeline beats the incumbents on quality" is **not** supported by this data.
"Beeline matches them on quality at 11–13% lower cost, and reads more easily
than caveman" is.

The section 5 result is a different matter: +0.70 on `answered` and +0.80 on
`complete` against beeline's own prior version, on the same prompts with three
control arms moving less than 0.1, is far outside this noise floor. Finding a
regression in one skill is a much easier measurement than separating two good
skills from each other.

## 7. What a real session says

Sections 1–6 measure one prompt, one answer, no tools. That is not what an agent
session looks like. This section instruments an actual working session — 1,133
turns of infrastructure debugging, deployment and code review across two repos,
12 MB of transcript — and the picture inverts.

### Where the money went

| bucket | tokens | cost | share |
|---|---:|---:|---:|
| cache **read** | 417,080,654 | $208 | 71% |
| cache **write** | 10,394,758 | $65 | 22% |
| **output** | 726,353 | $18 | **6%** |
| fresh input | 3,140 | ~$0 | 0% |
| **total** | | **~$292** | |

Costed at Opus rates. Output is 6% of spend. Within that output, assistant prose
was 11% and tool calls 51%, so **the prose an output-style skill governs is
0.7% of the bill**. Every word written in that session cost $0.95.

### The unit that matters is the turn, not the word

Every turn re-reads the whole conversation. Average context was **368k tokens per
turn**, about **$0.18** each at cache-read rates.

One extra round-trip therefore costs roughly a fifth of all the prose in the
entire session. Five of them erase everything rules 7–10 could ever save.

That is the mechanism behind section 4's defect. Pre-fix beeline had a **27%
follow-up rate** on tool prompts — it asked "What's your domain?" instead of
giving the command. Each follow-up is a turn. The placeholder fix was worth more
than every prose rule in the skill combined, and not one character of it is
about brevity.

### The largest single finding

Of 902 turns that made tool calls, **every one made exactly one call.**

| tool calls per turn | turns |
|---|---:|
| 1 | 902 (100%) |
| 2 or more | 0 |

The harness instructs batching independent calls. It did not happen once.
Batching a conservative third of them saves ~270 turns, about **$48** — fifty
times the session's entire prose budget.

### Before and after, in the same session

beeline was switched on partway through, so the transcript contains both:

| measure | before | after | change |
|---|---:|---:|---:|
| output tokens/msg, median | 488 | 547 | +12% |
| prose chars/msg, median | 1,301 | 988 | **−24%** |
| total prose chars | 144,258 | 155,307 | **+8%** |

Prose per message fell by a quarter. Total prose rose, because the message count
rose 32%. Net saving: none.

Two confounders, stated rather than hidden: the workload differs across the two
halves, and the level drifted repeatedly — the user asked "are you using
beeline?" seven times, which is what prompted the level hook in 0.2.0. The
"after" period is not cleanly beeline.

### What this changes

The −63% in section 3 is real for what it measures: output tokens, single-turn,
cached system prompt. It is not a claim about what a skill saves you in an agent
loop, and it should never have been read as one.

Rules 11–17 — filter at the source, quote the decisive line, don't re-read
context, batch independent calls, never trade a turn for brevity, write a file
once — are the half that moves the bill, because they keep bytes out of context
and turns off the clock. Rules 7–10 make output readable. That is a real benefit
and it is not a financial one.

## What this does not show

1. **No arm actually called a tool.** The harness has no tool loop, so the "tools" set measures how each skill *describes* doing the work — not whether it filters output at the source. Rules 11–14 remain untested in a live session.
2. **All three skills lose to plain baseline** if you make a handful of uncached calls (section 2).
3. **Layer 3 is arithmetic, not measurement.** The 0.1× cache-read multiplier is applied to measured token counts; no cached run was performed.
4. **One judge, one model.** Opus judging Sonnet's output. A second judge, or human scoring, could move the quality numbers; the size of the tools-set gap makes a full reversal unlikely but the exact figures are soft.
5. **n=30 per cell** is enough for a stable ranking and for detecting a large
   regression (section 5). It is not enough to separate beeline from
   i-have-adhd on quality — see section 6, where none of those gaps clear
   their confidence interval.

## Reproduce

```
# put OPENROUTER_API_KEY in .env.local at the repo root
python benchmarks/compare.py --set both --runs 3 --keep-text
python benchmarks/summarize.py benchmarks/results/<raw-file>.json
python benchmarks/judge.py benchmarks/results/<raw-file>.json
```

`--limit 2` runs a smoke test first. `--arms` selects a subset. `--model` overrides the model slug. `--keep-text` is required for judging.

Cost of the full run: roughly $3 — about $2 for the 240 Sonnet calls, $0.75 for the 60 Opus judging calls.
