# -*- coding: utf-8 -*-
"""Compare output-token cost of beeline vs caveman vs i-have-adhd vs baseline.

Four arms, identical prompts, identical model. Each arm puts one skill's
SKILL.md in the system prompt; baseline sends none. Token counts come from the
provider's usage field, never a local estimate.

Runs against OpenRouter (OpenAI-schema). Routes to a Claude model, because
these skills are written for Claude and measuring them elsewhere measures the
wrong thing.

Usage:
    python benchmarks/compare.py --set prose
    python benchmarks/compare.py --set tools
    python benchmarks/compare.py --set both --runs 2

Key: put OPENROUTER_API_KEY in .env.local at the repo root, or in the env.
"""
from __future__ import print_function

import argparse
import io
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://openrouter.ai/api/v1/chat/completions"
KEY_VAR = "OPENROUTER_API_KEY"

# Only this key is read from .env.local. Nothing else is exported.
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


# Arm name -> path to the SKILL.md whose body becomes the system prompt.
PLUGIN_CACHE = os.path.join(
    os.path.expanduser("~"), ".claude", "plugins", "cache"
)
ARMS = {
    "baseline": None,
    "caveman": os.path.join(
        PLUGIN_CACHE, "caveman", "caveman", "0d95a81d35a9",
        "skills", "caveman", "SKILL.md"
    ),
    "i-have-adhd": os.path.join(
        PLUGIN_CACHE, "i-have-adhd", "i-have-adhd", "0.1.0",
        "skills", "i-have-adhd", "SKILL.md"
    ),
    "beeline": os.path.join(REPO, "skills", "beeline", "SKILL.md"),
}

# Tool-heavy prompts. Caveman's own set is prose Q&A, which cannot exercise
# beeline's rules 11-14 (tool discipline) — the group where it claims its
# savings. Without these the benchmark only measures the half where caveman
# is expected to win.
TOOL_PROMPTS = [
    ("router-restart", "I restarted a systemd service on a remote box and want to know if it came back cleanly. Walk me through checking it."),
    ("find-port-ref", "Some config file in my repo references port 3461 and I need to find which one, then change it to 3462."),
    ("failed-deploy", "My deploy just failed. The web service is crash-looping. How do I find out why?"),
    ("log-scan", "I need to know if any errors happened in the last 24 hours across six systemd services on a production box."),
    ("db-check", "Check whether any users signed up today in a sqlite database at /opt/app/data/platform.db."),
    ("disk-full", "A server is reporting disk full. Find what is using the space and clear it safely."),
    ("git-drift", "A production box has uncommitted changes and I need to know what they are and whether they matter."),
    ("cert-expiry", "Find out when the TLS certificate for my domain expires."),
    ("stuck-container", "One Docker container out of forty is unhealthy. Identify which and why."),
    ("port-conflict", "Two processes seem to want the same port on this machine. Find them."),
]


def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip()
    return text


def load_prompts(which):
    out = []
    if which in ("prose", "both"):
        p = os.path.join(
            PLUGIN_CACHE, "caveman", "caveman", "0d95a81d35a9",
            "benchmarks", "prompts.json"
        )
        data = json.load(io.open(p, encoding="utf-8"))
        for item in data["prompts"]:
            out.append(("prose", item["id"], item["prompt"]))
    if which in ("tools", "both"):
        for pid, text in TOOL_PROMPTS:
            out.append(("tools", pid, text))
    return out


def call(key, model, system, prompt, max_tokens, timeout=120):
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0,
        "messages": ([{"role": "system", "content": system}] if system else [])
        + [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-Title": "beeline-benchmark",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    usage = data.get("usage") or {}
    text = ""
    if data.get("choices"):
        text = (data["choices"][0].get("message") or {}).get("content") or ""
    return {
        "completion_tokens": usage.get("completion_tokens"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "text": text,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="both", choices=["prose", "tools", "both"])
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.5")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=1200)
    ap.add_argument("--arms", default="baseline,caveman,i-have-adhd,beeline")
    ap.add_argument("--limit", type=int, default=0, help="cap prompts per set (smoke test)")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("No %s found. Put it in .env.local at the repo root." % KEY_VAR)
        return 2

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arms:
        if a not in ARMS:
            print("Unknown arm: %s" % a)
            return 2
        if ARMS[a] and not os.path.exists(ARMS[a]):
            print("Missing SKILL.md for arm %s: %s" % (a, ARMS[a]))
            return 2

    systems = {}
    for a in arms:
        systems[a] = (
            strip_frontmatter(io.open(ARMS[a], encoding="utf-8").read())
            if ARMS[a] else None
        )

    prompts = load_prompts(args.set)
    if args.limit:
        by_set = {}
        capped = []
        for s, pid, text in prompts:
            by_set.setdefault(s, 0)
            if by_set[s] < args.limit:
                capped.append((s, pid, text))
                by_set[s] += 1
        prompts = capped

    total_calls = len(prompts) * len(arms) * args.runs
    print("model=%s  arms=%d  prompts=%d  runs=%d  calls=%d"
          % (args.model, len(arms), len(prompts), args.runs, total_calls))

    records = []
    done = 0
    for pset, pid, text in prompts:
        for arm in arms:
            for run in range(args.runs):
                try:
                    r = call(key, args.model, systems[arm], text, args.max_tokens)
                except urllib.error.HTTPError as e:
                    print("HTTP %s on %s/%s: %s"
                          % (e.code, arm, pid, e.read().decode("utf-8")[:200]))
                    return 1
                except Exception as e:
                    print("FAIL %s/%s: %s" % (arm, pid, e))
                    return 1
                records.append({
                    "set": pset, "prompt_id": pid, "arm": arm, "run": run,
                    "completion_tokens": r["completion_tokens"],
                    "prompt_tokens": r["prompt_tokens"],
                    "chars": len(r["text"]),
                })
                done += 1
                print("  [%d/%d] %-12s %-22s out=%s"
                      % (done, total_calls, arm, pid, r["completion_tokens"]))
                time.sleep(0.4)

    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(REPO, "benchmarks", "results")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    raw_path = os.path.join(outdir, "raw-%s.json" % stamp)
    io.open(raw_path, "w", encoding="utf-8").write(
        json.dumps({"model": args.model, "records": records}, indent=1)
    )

    print("\n=== output tokens per response ===")
    sets = sorted(set(r["set"] for r in records))
    for pset in sets:
        print("\n[%s]" % pset)
        print("%-14s %8s %8s %8s %10s" % ("arm", "median", "mean", "n", "vs base"))
        base = None
        for arm in arms:
            vals = [r["completion_tokens"] for r in records
                    if r["set"] == pset and r["arm"] == arm
                    and r["completion_tokens"] is not None]
            if not vals:
                continue
            med = statistics.median(vals)
            mean = sum(vals) / float(len(vals))
            if arm == "baseline":
                base = mean
            delta = "" if base in (None, 0) else "%+.0f%%" % ((mean - base) / base * 100)
            print("%-14s %8.0f %8.0f %8d %10s" % (arm, med, mean, len(vals), delta))

    print("\nraw: %s" % raw_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
