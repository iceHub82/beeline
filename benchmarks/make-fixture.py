# -*- coding: utf-8 -*-
"""Generate the benchmark fixture: a small project with planted, findable faults.

Generated rather than checked in so the repo stays small and every run starts
from a byte-identical tree. Each fault has exactly one right answer, which is
what lets agent-loop.py check success without a judge.

    python benchmarks/make-fixture.py <dir>
"""
from __future__ import print_function
import io, os, shutil, sys

FILES = {
"README.md": """# orderly

Small order service. Nothing here is real.
""",

"config/service.yaml": """service:
  name: orderly
  port: 3461
  workers: 4
timeout_secs: 30
""",

"config/logging.yaml": """version: 1
handlers:
  console:
    level: INFO
""",

".env.example": """DATABASE_URL=postgres://localhost/orderly
API_TIMEOUT=30
CACHE_TTL=300
""",

".env": """DATABASE_URL=postgres://localhost/orderly
CACHE_TTL=300
""",

"requirements.txt": """flask==3.0.0
requests==2.19.1
pytest==8.0.0
pyyaml==6.0.1
""",

"src/__init__.py": "",

"src/pricing.py": '''"""Order pricing."""


def apply_discount(subtotal, percent):
    return subtotal - (subtotal * percent / 100)


def calculate_total(items):
    """Sum line totals. Returns the subtotal before tax."""
    total = 0
    for item in items:
        total += item["price"] * item["qty"]
    return total


def line_labels(items):
    """Human labels for each line, 1-indexed."""
    labels = []
    for i in range(len(items)):
        labels.append("Line %d" % i)
    return labels
''',

"src/orders.py": '''"""Order assembly."""
from .pricing import calculate_total, apply_discount


def build_order(items, discount_percent=0):
    subtotal = calculate_total(items)
    if discount_percent:
        subtotal = apply_discount(subtotal, discount_percent)
    return {"items": items, "subtotal": subtotal}
''',

"src/health.py": '''def check():
    return {"status": "ok"}
''',

"tests/test_pricing.py": '''from src.pricing import calculate_total, apply_discount, line_labels


def test_calculate_total():
    items = [{"price": 10, "qty": 2}, {"price": 5, "qty": 1}]
    assert calculate_total(items) == 25


def test_discount_applies():
    assert apply_discount(200, 10) == 180


def test_line_labels_are_one_indexed():
    labels = line_labels([{"price": 1, "qty": 1}, {"price": 2, "qty": 1}])
    assert labels[0] == "Line 1"
''',

"tests/test_health.py": '''from src.health import check


def test_check():
    assert check()["status"] == "ok"
''',

"docker-compose.yml": """services:
  api:
    image: orderly:latest
    ports:
      - "3461:3461"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3461/health"]
  worker:
    image: orderly:latest
    command: python -m src.worker
  cache:
    image: redis:7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
""",

"deploy/notes.md": """Deploy runs on two boxes. The port in config/service.yaml
must match the published port in docker-compose.yml.
""",
}

# One genuine failure buried in ordinary noise, so "quote the decisive line"
# is a real skill and not a one-line file.
def build_log():
    lines = []
    for i in range(120):
        lines.append("2026-08-01T09:%02d:%02dZ INFO  request served path=/orders status=200" % (i // 2, i % 60))
        if i % 17 == 0:
            lines.append("2026-08-01T09:%02d:%02dZ WARN  slow query 812ms table=orders" % (i // 2, i % 60))
    lines.insert(83, "2026-08-01T09:41:07Z ERROR connection refused: cache:6379 (redis unreachable)")
    lines.append("2026-08-01T10:02:11Z INFO  shutdown complete")
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = sys.argv[1]
    if os.path.isdir(root):
        shutil.rmtree(root)
    for rel, body in FILES.items():
        p = os.path.join(root, rel.replace("/", os.sep))
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        io.open(p, "w", encoding="utf-8", newline="\n").write(body)
    logp = os.path.join(root, "logs")
    os.makedirs(logp)
    io.open(os.path.join(logp, "app.log"), "w", encoding="utf-8", newline="\n").write(build_log())
    print("fixture written to %s (%d files)" % (root, len(FILES) + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
