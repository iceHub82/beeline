# -*- coding: utf-8 -*-
"""Blind quality scoring for benchmark responses.

The token benchmark measures cost. This measures whether the output is still
worth reading — without it, the degenerate optimum is a skill that says
nothing (100% savings, zero value).

Method: for each prompt, the four arms' responses are shown to a judge model
BLIND (arm names stripped) and in RANDOMISED order, scored on a fixed rubric.
Randomisation matters because judges have position bias; the mapping from
label back to arm is kept client-side and never shown to the judge.

Usage:
    python benchmarks/judge.py benchmarks/results/raw-...json
    python benchmarks/judge.py <raw> --judge anthropic/claude-opus-4.8

Requires responses captured with --keep-text (compare.py stores response text
only when that flag is set).
"""
from __future__ import print_function

import argparse
import io
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://openrouter.ai/api/v1/chat/completions"
KEY_VAR = "OPENROUTER_API_KEY"

RUBRIC = """You are grading assistant responses to the same user request.

You will see the user's request, then several candidate responses labelled A, B, C, D.
The labels are arbitrary and randomised — they carry no information about origin.

Score each response 1-5 on each criterion:

1. ANSWERED — does it actually address what was asked? (5 = fully; 1 = evades or answers something else)
2. ACTIONABLE — could the reader act on this without further clarification? (5 = yes, concrete next step or complete instructions; 1 = would need to ask a follow-up before doing anything)
3. COMPLETE — is anything load-bearing missing? Judge substance, not length. (5 = nothing important omitted; 1 = critical information absent)
4. READABLE — could a competent reader parse it on one pass? Terseness is fine; ambiguity, undefined shorthand, and unexplained jargon are not. (5 = clear on one read; 1 = must re-read or decode)

Brevity is NOT a virtue in itself here, and neither is length. A short response
that answers fully scores high. A long response that buries the answer scores
low on READABLE. A short response missing something essential scores low on
COMPLETE.

Also answer: FOLLOWUP — would a reasonable person need to send a clarifying
question before they could act? Answer exactly "yes" or "no".

Return ONLY valid JSON, no prose, in this exact shape:
{"A": {"answered": N, "actionable": N, "complete": N, "readable": N, "followup": "yes|no"},
 "B": {...}, "C": {...}, "D": {...}}
"""


def load_key():
    if os.environ.get(KEY_VAR):
        return os.environ[KEY_VAR]
    path = os.path.join(REPO, ".env.local")
    if os.path.exists(path):
        for line in io.open(path, encoding="utf-8").read().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == KEY_VAR:
                return v.strip().strip('"').strip("'")
    return None


def call(key, model, system, prompt, max_tokens=2000, timeout=180):
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-Title": "beeline-judge",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return (data["choices"][0].get("message") or {}).get("content") or ""


def extract_json(text):
    """Judges sometimes wrap JSON in fences or prose. Take the outermost object."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in judge reply: %s" % text[:200])
    return json.loads(text[start:end + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", help="raw-*.json from compare.py (needs --keep-text)")
    ap.add_argument("--judge", default="anthropic/claude-opus-4.8")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("No %s found. Put it in .env.local at the repo root." % KEY_VAR)
        return 2

    data = json.load(io.open(args.raw, encoding="utf-8"))
    recs = data["records"]
    if not any(r.get("text") for r in recs):
        print("This raw file has no response text — re-run compare.py with --keep-text.")
        return 2

    # group by (set, prompt_id, run) so each judging call compares like with like
    groups = {}
    for r in recs:
        groups.setdefault((r["set"], r["prompt_id"], r.get("run", 0)), []).append(r)

    rng = random.Random(args.seed)
    labels = ["A", "B", "C", "D", "E", "F"]
    scored = []
    keys = sorted(groups.keys())
    print("judge=%s  groups=%d" % (args.judge, len(keys)))

    for i, gk in enumerate(keys, 1):
        rows = [r for r in groups[gk] if r.get("text")]
        if len(rows) < 2:
            continue
        rng.shuffle(rows)
        mapping = {}
        parts = ["USER REQUEST:\n%s\n" % rows[0].get("prompt_text", "(prompt text unavailable)")]
        for label, row in zip(labels, rows):
            mapping[label] = row["arm"]
            parts.append("\n--- RESPONSE %s ---\n%s\n" % (label, row["text"]))

        try:
            reply = call(key, args.judge, RUBRIC, "".join(parts))
            verdict = extract_json(reply)
        except urllib.error.HTTPError as e:
            print("HTTP %s: %s" % (e.code, e.read().decode("utf-8")[:200]))
            return 1
        except Exception as e:
            print("group %s failed: %s" % (str(gk), e))
            continue

        for label, arm in mapping.items():
            v = verdict.get(label)
            if not isinstance(v, dict):
                continue
            scored.append({
                "set": gk[0], "prompt_id": gk[1], "run": gk[2], "arm": arm,
                "answered": v.get("answered"), "actionable": v.get("actionable"),
                "complete": v.get("complete"), "readable": v.get("readable"),
                "followup": str(v.get("followup", "")).strip().lower(),
            })
        print("  [%d/%d] %-22s scored" % (i, len(keys), gk[1]))
        time.sleep(0.4)

    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(REPO, "benchmarks", "results")
    out = os.path.join(outdir, "judged-%s.json" % stamp)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps({"judge": args.judge, "source": os.path.basename(args.raw),
                    "scores": scored}, indent=1)
    )

    arms = []
    for s in scored:
        if s["arm"] not in arms:
            arms.append(s["arm"])

    print("\n=== quality (1-5, higher is better) ===")
    print("%-14s %9s %10s %9s %9s %11s %5s"
          % ("arm", "answered", "actionable", "complete", "readable", "followup%", "n"))
    for arm in arms:
        rows = [s for s in scored if s["arm"] == arm]
        if not rows:
            continue
        def avg(field):
            vals = [s[field] for s in rows if isinstance(s[field], (int, float))]
            return statistics.mean(vals) if vals else float("nan")
        fu = [s for s in rows if s["followup"] in ("yes", "no")]
        fu_rate = (100.0 * sum(1 for s in fu if s["followup"] == "yes") / len(fu)) if fu else float("nan")
        print("%-14s %9.2f %10.2f %9.2f %9.2f %10.0f%% %5d"
              % (arm, avg("answered"), avg("actionable"), avg("complete"),
                 avg("readable"), fu_rate, len(rows)))

    print("\njudged: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
