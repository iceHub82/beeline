# Benchmarks

Measured comparison of `beeline` against the two skills it merges — [`caveman`](https://github.com/JuliusBrussee/caveman) (prose compression) and [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) (actionable structure) — plus an unmodified baseline.

Run 2026-07-29. Raw data and the harness are in this directory; every number below is reproducible with one command.

**Read section 4 before quoting section 1.** On tool-shaped work beeline buys its token savings partly by not answering the question. That is a defect in the skill, and the numbers below are the evidence for it.

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

**Tools — beeline is last in three of four columns:**

| arm | answered | actionable | complete | readable | needs follow-up |
|---|---:|---:|---:|---:|---:|
| baseline | **4.63** | **4.60** | **4.70** | 3.90 | 10% |
| caveman | 4.53 | 4.57 | 4.27 | 4.53 | 20% |
| i-have-adhd | 4.37 | 4.47 | 3.90 | **4.97** | 23% |
| beeline | 3.97 | 3.97 | **3.20** | 4.70 | **27%** |

Beeline is the *most readable* compressed arm and the *least complete* arm in the benchmark. It saves the most tokens on tool work and answers the question least often. Those are the same fact.

Two verbatim examples, both real responses to the tool prompts:

> **"Find out when the TLS certificate for my domain expires."**
> beeline, 8 tokens, COMPLETE = 1.00: *"What's your domain?"*
> i-have-adhd, 84 tokens, COMPLETE = 5.00: the full `openssl s_client … | openssl x509 -noout -dates` command with `yourdomain.com` as a placeholder and a note that `notAfter=` is the date.

> **"A server is reporting disk full. Find what is using the space and clear it safely."**
> beeline, 24 tokens: `df -h` and *"Need to see which filesystem is full and where to look."*
> caveman, 309 tokens: `df -h`, `du -sh /*`, then log/Docker/package-cache/tmp/old-kernel cleanup with the actual commands.

The second is arguably over-answering. The first is simply not answering — a placeholder domain costs nine tokens and turns a 27% follow-up rate into zero.

**Diagnosis.** Beeline's "real ambiguity — one short clarifying question beats guessing" override fires too easily on tool-shaped prompts, where its tool-discipline rules already push toward a bare command. The two compose into "ask instead of answer." The prose rules are not implicated: prose scores are the best in the benchmark.

## What this does not show

1. **No arm actually called a tool.** The harness has no tool loop, so the "tools" set measures how each skill *describes* doing the work — not whether it filters output at the source. Rules 11–14 remain untested in a live session.
2. **All three skills lose to plain baseline** if you make a handful of uncached calls (section 2).
3. **Layer 3 is arithmetic, not measurement.** The 0.1× cache-read multiplier is applied to measured token counts; no cached run was performed.
4. **One judge, one model.** Opus judging Sonnet's output. A second judge, or human scoring, could move the quality numbers; the size of the tools-set gap makes a full reversal unlikely but the exact figures are soft.
5. **n=30 per cell** is enough for a stable ranking, not for confidence intervals.

## Reproduce

```
# put OPENROUTER_API_KEY in .env.local at the repo root
python benchmarks/compare.py --set both --runs 3 --keep-text
python benchmarks/summarize.py benchmarks/results/<raw-file>.json
python benchmarks/judge.py benchmarks/results/<raw-file>.json
```

`--limit 2` runs a smoke test first. `--arms` selects a subset. `--model` overrides the model slug. `--keep-text` is required for judging.

Cost of the full run: roughly $3 — about $2 for the 240 Sonnet calls, $0.75 for the 60 Opus judging calls.
