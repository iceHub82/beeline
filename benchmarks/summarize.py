# -*- coding: utf-8 -*-
"""Net token cost per response — output savings vs the input cost of the skill itself.

Percentages on output tokens alone flatter whichever skill has the largest
SKILL.md, because that file is re-sent as the system prompt on every call.
This reports both sides.
"""
from __future__ import print_function

import io
import json
import statistics
import sys


def main(path):
    data = json.load(io.open(path, encoding="utf-8"))
    recs = data["records"]
    arms, sets = [], []
    for r in recs:
        if r["arm"] not in arms:
            arms.append(r["arm"])
        if r["set"] not in sets:
            sets.append(r["set"])

    print("model:", data.get("model"), " records:", len(recs))
    for pset in sets:
        print("\n[%s]" % pset)
        print("%-14s %9s %9s %9s %10s" % ("arm", "in/call", "out/call", "total", "vs base"))
        base_total = None
        for arm in arms:
            rows = [r for r in recs if r["set"] == pset and r["arm"] == arm]
            if not rows:
                continue
            tin = statistics.mean([r["prompt_tokens"] or 0 for r in rows])
            tout = statistics.mean([r["completion_tokens"] or 0 for r in rows])
            total = tin + tout
            if arm == "baseline":
                base_total = total
            delta = "" if not base_total else "%+.0f%%" % ((total - base_total) / base_total * 100)
            print("%-14s %9.0f %9.0f %9.0f %10s" % (arm, tin, tout, total, delta))

    # Weighted cost at Sonnet rates: input is ~1/5 the price of output.
    print("\n[cost-weighted, input x1 / output x5 — Sonnet ratio]")
    print("%-14s %12s %10s" % ("arm", "weighted", "vs base"))
    base_w = None
    for arm in arms:
        rows = [r for r in recs if r["arm"] == arm]
        tin = statistics.mean([r["prompt_tokens"] or 0 for r in rows])
        tout = statistics.mean([r["completion_tokens"] or 0 for r in rows])
        w = tin + 5 * tout
        if arm == "baseline":
            base_w = w
        delta = "" if not base_w else "%+.0f%%" % ((w - base_w) / base_w * 100)
        print("%-14s %12.0f %10s" % (arm, w, delta))


    # Real sessions cache the system prompt: cache reads bill at ~0.1x input.
    # The skill file is written once, then read on every later call.
    print("\n[cached system prompt, input x0.1 / output x5 — the real-session case]")
    print("%-14s %12s %10s" % ("arm", "weighted", "vs base"))
    base_c = None
    for arm in arms:
        rows = [r for r in recs if r["arm"] == arm]
        tin = statistics.mean([r["prompt_tokens"] or 0 for r in rows])
        tout = statistics.mean([r["completion_tokens"] or 0 for r in rows])
        c = 0.1 * tin + 5 * tout
        if arm == "baseline":
            base_c = c
        delta = "" if not base_c else "%+.0f%%" % ((c - base_c) / base_c * 100)
        print("%-14s %12.0f %10s" % (arm, c, delta))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
