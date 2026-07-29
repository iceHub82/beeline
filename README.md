# beeline

Compressed, action-first output for Claude Code.

Merges the structural rules of [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) with the omission rules of [`caveman`](https://github.com/JuliusBrussee/caveman), drops article-stripping from the default, and adds a third rule group neither has: tool-output discipline.

## Why

`caveman` compresses prose. Its headline rule — dropping articles — saves almost nothing (`the` and `a` are single common tokens) while costing a beat of parsing on every line. Its valuable rules are the ones about what *not* to write.

`i-have-adhd` shapes output so it can be acted on: lead with the action, number sequences, restate state, end with one next action. Those rules spend tokens, which is what caveman deletes.

Neither addresses where the tokens actually go. In a working session, assistant prose is a minority of the total — tool results dominate.

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
