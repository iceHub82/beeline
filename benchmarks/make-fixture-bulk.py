# -*- coding: utf-8 -*-
"""Generate the BULK fixture: same shape of faults, buried in large output.

The small fixture answered "does beeline pay for itself on short tasks with
tiny tool results" — it does not, because a 1,700-token system prompt re-sent
each turn dwarfs the saving. That is the regime where filtering cannot win.

This fixture is the other regime. A 30,000-line log, 120 modules, a 60-test
suite. Naive commands here return enormous output; filtered ones return a line.
If the tool-discipline rules ever pay for themselves, it is here.

    python benchmarks/make-fixture-bulk.py <dir>
"""
from __future__ import print_function
import io, os, shutil, sys

PATHS = ["orders", "billing", "shipping", "catalog", "auth", "search"]


def w(root, rel, body):
    p = os.path.join(root, rel.replace("/", os.sep))
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)


def build_log():
    """30k lines. One ERROR, at line ~19,400, naming postgres."""
    out = []
    for i in range(30000):
        sec = i % 60
        mn = (i // 60) % 60
        hr = 6 + (i // 3600) % 18
        path = PATHS[i % len(PATHS)]
        ms = 20 + (i * 7) % 300
        out.append("2026-07-%02dT%02d:%02d:%02dZ INFO  path=/%s status=200 dur=%dms"
                   % (1 + (i // 8000), hr, mn, sec, path, ms))
        if i % 400 == 0:
            out.append("2026-07-%02dT%02d:%02d:%02dZ WARN  retry attempt=1 path=/%s"
                       % (1 + (i // 8000), hr, mn, sec, path))
    out.insert(19400, "2026-07-03T14:22:09Z ERROR could not connect to postgres:5432 "
                      "— order writes are failing")
    # one very slow request, so "find the slowest" needs sorting, not eyeballing
    out.insert(24100, "2026-07-04T08:11:52Z INFO  path=/catalog status=200 dur=9187ms")
    return "\n".join(out) + "\n"


def build_modules(root):
    """120 modules. `settle_ledger` is defined in exactly two of them."""
    for i in range(120):
        pkg = PATHS[i % len(PATHS)]
        body = ['"""Module %03d."""' % i, ""]
        body.append("def handler_%03d(payload):" % i)
        body.append("    return {'ok': True, 'id': payload.get('id')}")
        body.append("")
        if i in (37, 91):
            body.append("def settle_ledger(account, amount):")
            body.append("    return account.balance - amount")
            body.append("")
        if i == 64:
            body.append("# TODO: this retries forever if the queue is down")
            body.append("")
        if i in (12, 88, 103):
            body.append("# TODO: drop this once the migration lands")
            body.append("")
        w(root, "src/%s/mod_%03d.py" % (pkg, i), "\n".join(body))
    for pkg in PATHS:
        w(root, "src/%s/__init__.py" % pkg, "")
    w(root, "src/__init__.py", "")


def build_tests(root):
    """60 tests across 6 files. Exactly one fails."""
    for f in range(6):
        lines = ["import pytest", ""]
        for t in range(10):
            n = f * 10 + t
            if n == 43:
                lines += ["def test_ledger_settles_to_zero():",
                          "    assert 100 - 99 == 0", ""]
            else:
                lines += ["def test_case_%03d():" % n, "    assert True", ""]
        w(root, "tests/test_group_%d.py" % f, "\n".join(lines))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = sys.argv[1]
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)

    w(root, "README.md", "# bulk\n\nLarge synthetic service. Nothing here is real.\n")
    build_modules(root)
    build_tests(root)
    w(root, "logs/app.log", build_log())

    # requirements vs lockfile: exactly one package disagrees
    w(root, "requirements.txt",
      "flask==3.0.0\nrequests==2.31.0\npytest==8.0.0\npyyaml==6.0.1\nredis==5.0.1\n")
    w(root, "requirements.lock",
      "flask==3.0.0\nrequests==2.31.0\npytest==8.0.0\npyyaml==6.0.1\nredis==4.6.0\n")

    # one hardcoded credential, in one of 120 modules' neighbours
    w(root, "src/auth/legacy_client.py",
      '"""Deprecated client."""\n\nAPI_TOKEN = "sk-live-9f3a2b7c1d4e5f6a"\n\n'
      "def call(path):\n    return {'path': path}\n")

    print("bulk fixture written to %s" % root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
