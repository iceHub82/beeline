# -*- coding: utf-8 -*-
"""Paired beeline-vs-rival deltas with bootstrap CIs.

Same prompt, same run, same judging call -> pair them and bootstrap the mean
difference. A CI straddling zero means the gap is not distinguishable from
noise at n=30, however pretty the headline table looks.
"""
from __future__ import print_function
import io, json, random, statistics, collections

PROSE = r"C:\AgenticRepos\beeline\benchmarks\results\judged-20260729T132110Z.json"
TOOLS = r"C:\AgenticRepos\beeline\benchmarks\results\judged-20260729T134144Z.json"

def load(p, which):
    return [s for s in json.load(io.open(p, encoding="utf-8"))["scores"]
            if s["set"] == which]

FIELDS = ["answered", "actionable", "complete", "readable"]
rng = random.Random(7)

def boot(diffs, n=8000):
    if not diffs:
        return (float("nan"),) * 3
    means = []
    for _ in range(n):
        s = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        means.append(statistics.mean(s))
    means.sort()
    return statistics.mean(diffs), means[int(0.025 * n)], means[int(0.975 * n)]

for label, path in (("prose", PROSE), ("tools", TOOLS)):
    scores = load(path, label)
    idx = {}
    for s in scores:
        idx[(s["prompt_id"], s["run"], s["arm"])] = s
    keys = sorted({(s["prompt_id"], s["run"]) for s in scores})

    for rival in ("caveman", "i-have-adhd"):
        print("\n[%s]  beeline - %s   (positive = beeline better)" % (label, rival))
        for f in FIELDS:
            d = []
            for k in keys:
                a = idx.get((k[0], k[1], "beeline"))
                b = idx.get((k[0], k[1], rival))
                if a and b and isinstance(a[f], (int, float)) and isinstance(b[f], (int, float)):
                    d.append(a[f] - b[f])
            m, lo, hi = boot(d)
            verdict = "real" if (lo > 0 or hi < 0) else "NOISE"
            print("   %-11s %+5.2f   95%% CI [%+.2f, %+.2f]  %s" % (f, m, lo, hi, verdict))
