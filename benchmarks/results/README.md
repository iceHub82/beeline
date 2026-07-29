# Result files

Timestamps are UTC, from the run that produced them. Read [BENCHMARKS.md](../../BENCHMARKS.md)
for what the numbers mean; this file only says which run is which.

| file | run | n | notes |
|---|---|---|---|
| `raw-20260729T102415Z.json` | pilot, prose only | 2/cell | smoke test of the harness |
| `raw-20260729T103611Z.json` | first full run | 10/cell | one run per cell; superseded |
| `raw-20260729T131646Z.json` | **main run** | 30/cell | 3 runs, both sets, `--keep-text` |
| `judged-20260729T132110Z.json` | quality scoring of the above | 60 groups | found the under-answering defect |
| `raw-20260729T133914Z.json` | **tools re-run, post-fix** | 30/cell | after the placeholder rule landed |
| `judged-20260729T134144Z.json` | quality scoring of the above | 30 groups | confirmed the fix |

The headline tables in BENCHMARKS.md use `131646` for prose and `133914` for
tools — prose was not re-run, because the fix targets actionable requests and
the prose set barely exercises them. That is stated in the caveats there too.

`judged-*.json` files carry the per-response scores with arm names attached.
The judge itself never saw the arm names: `judge.py` randomises order and
strips labels, keeping the mapping client-side.

Regenerate any of this with the commands in BENCHMARKS.md → Reproduce.
