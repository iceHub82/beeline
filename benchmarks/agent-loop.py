# -*- coding: utf-8 -*-
"""Agent-loop benchmark: does beeline reduce turns and tokens on real tool work?

Every other benchmark in this directory sends one prompt and reads one reply.
That measures the 0.33% of an agent session that is visible prose. This one runs
an actual tool loop against a real filesystem and measures what the session
costs: turns taken, tokens billed across every turn, tool output pulled into
context, and — the part that stops a compressed arm winning by saying nothing —
whether the task was actually completed.

Two arms: no system prompt, and beeline's SKILL.md as the system prompt.

    python benchmarks/agent-loop.py --base-url http://172.17.0.1:4000 --key-file /opt/bedrock-proxy/master_key.txt
    python benchmarks/agent-loop.py --limit 2          # smoke test
"""
from __future__ import print_function

import argparse
import io
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "beeline", "SKILL.md")
MAKE_FIXTURE = os.path.join(REPO, "benchmarks", "make-fixture.py")

# ---------------------------------------------------------------- tasks

def has_number(n):
    """Answer check for a count: the number must appear as its own token.

    A bare substring test is useless here — "1" appears in nearly any sentence
    and "7" appears in a timestamp.
    """
    import re
    pat = re.compile(r"(?<![\d.])%d(?![\d.])" % n)

    def check(answer, root):
        return bool(pat.search(answer or ""))
    return check


def has(*needles):
    """Answer check: every needle must appear in the final reply."""
    def check(answer, root):
        low = answer.lower()
        return all(n.lower() in low for n in needles)
    return check


def file_contains(rel, needle):
    def check(answer, root):
        try:
            return needle in io.open(os.path.join(root, rel), encoding="utf-8").read()
        except Exception:
            return False
    return check


def file_lacks(rel, needle):
    def check(answer, root):
        try:
            return needle not in io.open(os.path.join(root, rel), encoding="utf-8").read()
        except Exception:
            return False
    return check


def both(a, b):
    return lambda answer, root: a(answer, root) and b(answer, root)


# 12 tasks. Each has exactly one right answer, checkable without a judge.
TASKS = [
    ("find-port-file",
     "Which file in this project sets the service port? Answer with the path.",
     has("config/service.yaml")),

    ("change-port",
     "The service port must change from 3461 to 3462 everywhere it is configured. Make the change.",
     both(file_contains("config/service.yaml", "3462"),
          file_lacks("config/service.yaml", "3461"))),

    ("failing-test",
     "One test in this project fails. Name the failing test function.",
     has("test_line_labels_are_one_indexed")),

    ("fix-failing-test",
     "One test fails because of an off-by-one in src/pricing.py. Fix the source, not the test.",
     both(file_contains("src/pricing.py", "i + 1"),
          file_lacks("tests/test_pricing.py", "Line 0"))),

    ("count-errors",
     "How many ERROR lines are in logs/app.log? Answer with the number only.",
     has_number(1)),

    ("the-real-error",
     "logs/app.log contains one genuine failure. What service was unreachable?",
     has("redis")),

    ("stale-dep",
     "Which dependency in requirements.txt is on a badly outdated major version? Name the package.",
     has("requests")),

    ("missing-env",
     "One variable in .env.example is missing from .env. Which one?",
     has("API_TIMEOUT")),

    ("no-healthcheck",
     "Which service in docker-compose.yml has no healthcheck? Name the service.",
     has("worker")),

    ("count-python",
     "How many .py files are in this project? Answer with the number only.",
     has_number(6)),

    ("port-mismatch",
     "deploy/notes.md says two files must agree on the port. Do they currently agree? Answer yes or no and name both files.",
     both(has("config/service.yaml"), has("docker-compose.yml"))),

    ("add-healthcheck",
     "Add a healthcheck to the worker service in docker-compose.yml that runs: CMD python -m src.health",
     file_contains("docker-compose.yml", "src.health")),
]

# ---------------------------------------------------------------- tools

TOOLS = [
    {"type": "function", "function": {
        "name": "bash",
        "description": "Run a shell command in the project directory. Returns stdout and stderr.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "The shell command to run."}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a file, relative to the project root.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write a file, relative to the project root. Overwrites.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
]

MAX_RESULT = 20000   # a single tool result is truncated here, as a real harness would


def run_bash(command, root, use_docker):
    """Shell, isolated.

    This executes model-generated commands on whatever host the benchmark runs
    on — in practice a production box, because that is where the Bedrock proxy
    lives. Docker with no network and only the fixture mounted means the worst
    case is a destroyed copy of a throwaway directory.
    """
    if use_docker:
        argv = ["docker", "run", "--rm", "--network", "none",
                "-v", "%s:/w" % os.path.abspath(root), "-w", "/w",
                "alpine:3.20", "sh", "-c", command]
    else:
        argv = ["sh", "-c", command]
    try:
        p = subprocess.run(argv, cwd=None if use_docker else root, capture_output=True,
                           timeout=30, text=True, errors="replace")
        return ((p.stdout or "") + (p.stderr or "")) or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out after 30s)"
    except Exception as e:
        return "(failed to run: %s)" % e


def safe_path(root, rel):
    full = os.path.abspath(os.path.join(root, rel.lstrip("/")))
    if not full.startswith(os.path.abspath(root)):
        raise ValueError("path escapes the project root")
    return full


def exec_tool(name, args, root, use_docker):
    try:
        if name == "bash":
            return run_bash(args.get("command", ""), root, use_docker)
        if name == "read_file":
            return io.open(safe_path(root, args.get("path", "")), encoding="utf-8",
                           errors="replace").read()
        if name == "write_file":
            p = safe_path(root, args.get("path", ""))
            d = os.path.dirname(p)
            if d and not os.path.isdir(d):
                os.makedirs(d)
            io.open(p, "w", encoding="utf-8", newline="\n").write(args.get("content", ""))
            return "written"
        return "unknown tool: %s" % name
    except Exception as e:
        return "error: %s" % e


# ---------------------------------------------------------------- model

def call(url, key, model, messages, max_tokens, timeout=180):
    body = {"model": model, "max_tokens": max_tokens, "temperature": 0,
            "messages": messages, "tools": TOOLS}
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def run_task(url, key, model, system, task, cap, use_docker, keep_text):
    tid, prompt, check = task
    root = tempfile.mkdtemp(prefix="beeline-fx-")
    subprocess.run([sys.executable, MAKE_FIXTURE, root], capture_output=True)

    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content":
                     prompt + "\n\nThe project is the current directory. "
                              "Answer when you are done."})

    turns = 0
    pt = ct = 0
    tool_chars = 0
    tool_calls = 0
    answer = ""
    capped = False
    t0 = time.time()

    while True:
        if turns >= cap:
            capped = True
            break
        turns += 1
        try:
            data = call(url, key, model, messages, 2000)
        except urllib.error.HTTPError as e:
            return {"error": "HTTP %s: %s" % (e.code, e.read().decode("utf-8")[:200])}
        except Exception as e:
            return {"error": str(e)}

        usage = data.get("usage") or {}
        pt += usage.get("prompt_tokens") or 0
        ct += usage.get("completion_tokens") or 0

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        calls = msg.get("tool_calls") or []
        messages.append({"role": "assistant",
                         "content": msg.get("content") or "",
                         "tool_calls": calls} if calls else
                        {"role": "assistant", "content": msg.get("content") or ""})

        if not calls:
            answer = msg.get("content") or ""
            break

        for c in calls:
            tool_calls += 1
            fn = (c.get("function") or {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            out = exec_tool(fn.get("name") or "", args, root, use_docker)
            out = out[:MAX_RESULT]
            tool_chars += len(out)
            messages.append({"role": "tool", "tool_call_id": c.get("id"),
                             "content": out})

    ok = False
    try:
        ok = bool(check(answer, root)) and not capped
    except Exception:
        ok = False

    rec = {"task": tid, "turns": turns, "capped": capped,
           "prompt_tokens": pt, "completion_tokens": ct,
           "total_tokens": pt + ct, "tool_calls": tool_calls,
           "tool_result_chars": tool_chars, "success": ok,
           "seconds": round(time.time() - t0, 1)}
    if keep_text:
        rec["answer"] = answer[:2000]
    shutil.rmtree(root, ignore_errors=True)
    return rec


# ---------------------------------------------------------------- main

def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip()
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://172.17.0.1:4000")
    ap.add_argument("--key-file", default="/opt/bedrock-proxy/master_key.txt")
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--cap", type=int, default=12, help="turn cap; hitting it is a failure")
    ap.add_argument("--limit", type=int, default=0, help="run only the first N tasks")
    ap.add_argument("--no-docker", action="store_true",
                    help="run bash directly instead of in a container (unsafe on a shared host)")
    ap.add_argument("--keep-text", action="store_true")
    args = ap.parse_args()

    key = io.open(args.key_file, encoding="utf-8").read().strip()
    system = strip_frontmatter(io.open(SKILL, encoding="utf-8").read())
    arms = [("baseline", None), ("beeline", system)]
    tasks = TASKS[:args.limit] if args.limit else TASKS

    print("model=%s tasks=%d arms=%d cap=%d docker=%s"
          % (args.model, len(tasks), len(arms), args.cap, not args.no_docker))

    records = []
    for task in tasks:
        for arm, sysprompt in arms:
            r = run_task(args.base_url, key, args.model, sysprompt, task,
                         args.cap, not args.no_docker, args.keep_text)
            if "error" in r:
                print("  %-18s %-9s ERROR %s" % (task[0], arm, r["error"][:80]))
                continue
            r["arm"] = arm
            records.append(r)
            print("  %-18s %-9s turns=%-3d tok=%-7d tool_chars=%-6d %s"
                  % (task[0], arm, r["turns"], r["total_tokens"],
                     r["tool_result_chars"], "OK" if r["success"] else "FAIL"))

    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(REPO, "benchmarks", "results")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    path = os.path.join(outdir, "agentloop-%s.json" % stamp)
    io.open(path, "w", encoding="utf-8").write(json.dumps(
        {"model": args.model, "cap": args.cap, "records": records}, indent=1))

    print("\n%-10s %7s %9s %11s %10s %8s" %
          ("arm", "tasks", "success", "med turns", "med tokens", "tool ch"))
    for arm, _ in arms:
        rows = [r for r in records if r["arm"] == arm]
        if not rows:
            continue
        print("%-10s %7d %8.0f%% %11.0f %10.0f %8.0f" % (
            arm, len(rows), 100.0 * sum(1 for r in rows if r["success"]) / len(rows),
            statistics.median([r["turns"] for r in rows]),
            statistics.median([r["total_tokens"] for r in rows]),
            statistics.median([r["tool_result_chars"] for r in rows])))
    print("\nraw: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
