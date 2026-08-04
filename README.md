# beeline

Compressed, action-first output for Claude Code.

Merges the structural rules of [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) with the omission rules of [`caveman`](https://github.com/JuliusBrussee/caveman), drops article-stripping from the default, and expands caveman's single rule about tool output into a rule group of its own.

## Why

`caveman` compresses prose. Its headline rule — dropping articles — saves almost nothing (`the` and `a` are single common tokens) while costing a beat of parsing on every line. Its valuable rules are the ones about what *not* to write.

`i-have-adhd` shapes output so it can be acted on: lead with the action, number sequences, restate state, end with one next action. Those rules spend tokens, which is what caveman deletes.

Neither says much about where the tokens actually go. In a working session, assistant prose is a minority of the total — tool results dominate. caveman has one clause on this (don't dump raw error logs, quote the shortest decisive line); `i-have-adhd` has none. beeline turns that clause into four rules: filter at the source, quote the decisive line, don't re-read what's already in context, verify with the narrowest check that would fail if the change broke.

## Measured

**Start here, because the headline number below is the least useful one.** Instrumented against a real 1,133-turn agent session — 12 MB of transcript, two repos, infrastructure work — the budget splits like this:

| bucket | share of spend |
|---|---:|
| context re-read each turn (cache) | 93% |
| output tokens | 6% |
| of which, model reasoning | 4.4% |
| **of which, visible prose** | **0.33%** |

All the prose written in that session — every word of it combined — cost **$0.96** of a $292 bill. A single extra round-trip cost $0.18, so five clarifying questions erase everything prose compression could ever save. Meanwhile 902 turns made tool calls and every one made exactly one call; batching a third of them would have saved roughly $48, fifty times the entire prose budget.

That is why rules 11–18 (filter at source, batch independent calls, never trade a turn for brevity, write a file once, never read an empty result as an answer) are the half that moves the bill, and rules 7–10 are the half that makes output readable.

**An agent-loop benchmark — real tools, real filesystem, 12 tasks with deterministic checks — says whether that pays depends entirely on your workload.**

| | small files, quick greps | large logs and test suites |
|---|---:|---:|
| baseline tokens | 64,432 | 249,536 |
| beeline tokens | 147,813 | **216,750** |
| | **+129%** | **−13%** |
| tool output into context | −57% | −67% |
| tasks completed | 10/12 vs 12/12 | 10/12 vs 10/12 |

Same skill, same harness, opposite verdicts. Overhead is fixed — ~1,700 tokens of `SKILL.md` re-sent every turn — while the saving scales with how much output a naive command would drag into context. On the task where that meant a 30,000-line log, beeline used **81% fewer tokens**. On counting four TODOs, it used 498% more.

**Below about one system-prompt's worth of tool output per turn, this skill costs you money. Above it, it pays several times over.** Full numbers in [BENCHMARKS.md](BENCHMARKS.md) section 8.

**Both agent-loop runs were uncached** — every turn paid full price for the system prompt. Claude Code caches it at roughly 0.1×, which would cut that overhead about tenfold and pull the small-task penalty toward break-even. That is arithmetic, not a measurement; no cached comparison has been run.

The saving that holds in every run regardless: **57–67% less tool output pulled into context.** That barely moves the bill, but it means more turns before compaction.

With that established, the single-turn benchmark: 240 calls against caveman's own set plus a tool-shaped set, `claude-sonnet-4.5`, system prompt cached, n=30 per cell.

| arm | output tokens saved |
|---|---:|
| caveman | −58% |
| i-have-adhd | −57% |
| **beeline** | **−63%** |

True for what it measures — output tokens, one prompt, one answer, no tool loop. In the real session above, the same skill produced **no net saving at all**: prose per message fell 24%, message count rose 32%.

**That benchmark ran against 0.1.0.** Rules 15–17 and the level hook came later and have not been re-benchmarked; the single-turn numbers describe an earlier, shorter `SKILL.md`. Nothing in 0.3.0's economic argument rests on them, but they are not a measurement of the current skill.

The same responses were then scored blind by a second model, which is the number worth caring about — a skill that saves tokens by saying nothing would win the table above.

| tools set | answered | actionable | complete | readable |
|---|---:|---:|---:|---:|
| baseline | 4.63 | 4.60 | **4.77** | 3.83 |
| caveman | 4.53 | 4.57 | 4.13 | 4.50 |
| i-have-adhd | 4.43 | 4.53 | 3.90 | **5.00** |
| **beeline** | **4.67** | **4.73** | 4.00 | 4.97 |

That scoring caught a real defect first time round: beeline was last in three of four columns, answering *"What's your domain?"* in eight tokens when asked how to check a TLS certificate's expiry. One rule change — answer with a placeholder, then ask — moved answered 3.97 → 4.67 and follow-up rate 27% → 17% for two points of token saving.

**Don't over-read the quality table.** Cluster bootstrap CIs — resampling whole prompts, not prompt-run rows, since 30 rows are only 10 unique tasks — say beeline is meaningfully more readable than caveman (+0.70 prose, +0.47 tools) and otherwise indistinguishable from both parents on quality. The honest claim is *same quality, 11–13% cheaper, easier to read than caveman* — not "better". Numbers, intervals, control arms and the residual weakness (completeness, still below baseline) are in **[BENCHMARKS.md](BENCHMARKS.md)**.

Also worth knowing: counting total tokens rather than output tokens, every skill here — beeline included — costs *more* than no skill at all on uncached calls, and no arm actually called a tool.

## Install

```
/plugin marketplace add iceHub82/beeline
/plugin install beeline
```

From a local clone instead: `/plugin marketplace add C:\AgenticRepos\beeline`

Then:

```
/beeline
```

## Levels

| Level | Prose |
|-------|-------|
| lite | Grammatical, filler cut |
| full | Stripped, fragments in status lines (default) |
| ultra | Telegraphic, articles dropped |

Levels change prose only. Numbered steps, state restatement, the single next action, and tool discipline are identical at every level.

Off: `stop beeline` or `normal mode`.

**Activation is global, not per project.** The level lives in `~/.claude/.beeline-level`, so turning it on in one repo applies it to every Claude Code session on that machine until you turn it off.

## What it will not do

- Compress a safety confirmation before a destructive action
- Compress code, commits, PRs, or config
- Answer "what are my options" with one option
- Auto-activate — it is inert until you type `/beeline`. A hook restates the level you chose on each turn, but never picks one

## With other skills

Supersedes `caveman` and `i-have-adhd` — running them together is contradictory.

Composes with `ponytail`: ponytail governs what gets built, beeline governs how it is reported.

## Tests

```
node --test
```

## Licence

MIT
