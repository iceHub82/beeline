# Benchmarks

Measured comparison of `beeline` against the two skills it merges — [`caveman`](https://github.com/JuliusBrussee/caveman) (prose compression) and [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) (actionable structure) — plus an unmodified baseline.

Run 2026-07-29. Raw data and the harness are in this directory; every number below is reproducible with one command.

## Method

Four arms, identical prompts, identical model, `temperature: 0`. Each arm loads one skill's `SKILL.md` as the system prompt; baseline sends none. Token counts come from the provider's `usage` field, never a local estimate.

- **Model:** `anthropic/claude-sonnet-4.5` via OpenRouter
- **Prompts:** caveman's own 10-prompt set (prose Q&A) + 10 tool-shaped prompts written for this comparison
- **Calls:** 80 (20 prompts × 4 arms × 1 run) — n=10 per cell

Caveman's prompt set was used deliberately: it is the incumbent's own benchmark, so the prose comparison cannot be accused of being rigged for the challenger. The tool set exists because a prose-only benchmark cannot exercise beeline's tool-discipline rules (11–14), which is where it claims its savings.

## Results

### 1. Output tokens per response

What caveman's "65% measured" headline claims. Lower is better.

| arm | prose | tools |
|---|---:|---:|
| baseline | — | — |
| caveman | −56% | −66% |
| i-have-adhd | −58% | −71% |
| **beeline** | **−64%** | **−76%** |

Caveman's own claim reproduces closely on its own prompt set.

### 2. Total tokens per call — the number that inverts the headline

Every skill costs **more** than baseline once the system prompt is counted. The `SKILL.md` is re-sent on every call: ~1,700 input tokens shipped to save ~500 output tokens.

| arm | prose | tools |
|---|---:|---:|
| caveman | +97% | +205% |
| i-have-adhd | +146% | +292% |
| beeline | +133% | +275% |

Weighted at Sonnet's 1:5 input:output price ratio, with **no caching**:

| arm | vs baseline |
|---|---:|
| caveman | −18% |
| i-have-adhd | −8% |
| beeline | −16% |

Caveman edges ahead here, purely because its file is smaller.

### 3. Cached system prompt — the real-session case

A real session caches the system prompt; cache reads bill at roughly 0.1× input. This is the number that reflects actual use.

| arm | vs baseline |
|---:|---:|
| caveman | −55% |
| i-have-adhd | −57% |
| **beeline** | **−63%** |

beeline saves about **63%**, roughly 8 points better than caveman. The margin comes from tool-shaped work (−76% vs −66%) — the category caveman's prose-only benchmark never measures.

## What this does not show

Stated plainly, because the headline numbers above are easy to over-read:

1. **n=10 per cell, one run, one model.** Enough to be indicative, not enough for confidence intervals. Individual prompts varied 176–393 tokens across arms.
2. **No arm actually called a tool.** The harness has no tool loop, so the "tools" set measures how each skill *describes* doing the work — not whether it filters output at the source. Rules 11–14 remain untested in a live session.
3. **All three skills lose to plain baseline** if you make a handful of uncached calls. The saving depends on the system prompt being cached across a session.
4. **Layer 3 is arithmetic, not measurement.** The 0.1× cache-read multiplier is applied to measured token counts; no cached run was performed.

## Reproduce

```
# put OPENROUTER_API_KEY in .env.local at the repo root
python benchmarks/compare.py --set both
python benchmarks/summarize.py benchmarks/results/<raw-file>.json
```

`--limit 2` runs a 16-call smoke test first. `--arms` selects a subset. `--model` overrides the model slug.

Cost of the full 80-call run: roughly $0.60–0.90 at Sonnet rates.
