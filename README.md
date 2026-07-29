# beeline

Compressed, action-first output for Claude Code.

Merges the structural rules of [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) with the omission rules of [`caveman`](https://github.com/JuliusBrussee/caveman), drops article-stripping from the default, and adds a third rule group neither has: tool-output discipline.

## Why

`caveman` compresses prose. Its headline rule — dropping articles — saves almost nothing (`the` and `a` are single common tokens) while costing a beat of parsing on every line. Its valuable rules are the ones about what *not* to write.

`i-have-adhd` shapes output so it can be acted on: lead with the action, number sequences, restate state, end with one next action. Those rules spend tokens, which is what caveman deletes.

Neither addresses where the tokens actually go. In a working session, assistant prose is a minority of the total — tool results dominate.

## Measured

240 calls against caveman's own benchmark plus a tool-shaped prompt set, on `claude-sonnet-4.5`, with the system prompt cached as it is in a real session. n=30 per cell.

| arm | output tokens saved |
|---|---:|
| caveman | −58% |
| i-have-adhd | −57% |
| **beeline** | **−63%** |

The same responses were then scored blind by a second model, which is the number worth caring about — a skill that saves tokens by saying nothing would win the table above.

| tools set | answered | actionable | complete | readable |
|---|---:|---:|---:|---:|
| baseline | 4.63 | 4.60 | **4.77** | 3.83 |
| caveman | 4.53 | 4.57 | 4.13 | 4.50 |
| i-have-adhd | 4.43 | 4.53 | 3.90 | **5.00** |
| **beeline** | **4.67** | **4.73** | 4.00 | 4.97 |

That scoring caught a real defect first time round: beeline was last in three of four columns, answering *"What's your domain?"* in eight tokens when asked how to check a TLS certificate's expiry. One rule change — answer with a placeholder, then ask — moved answered 3.97 → 4.67 and follow-up rate 27% → 17% for two points of token saving. The before, after, control arms and the residual weakness (completeness, still below baseline) are in **[BENCHMARKS.md](BENCHMARKS.md)**.

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

## What it will not do

- Compress a safety confirmation before a destructive action
- Compress code, commits, PRs, or config
- Answer "what are my options" with one option
- Auto-activate — there are no hooks; it is inert until you type `/beeline`

## With other skills

Supersedes `caveman` and `i-have-adhd` — running them together is contradictory.

Composes with `ponytail`: ponytail governs what gets built, beeline governs how it is reported.

## Tests

```
node --test
```

## Licence

MIT
