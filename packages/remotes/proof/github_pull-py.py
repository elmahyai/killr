import json
import statistics
import time
from pathlib import Path

from remotes.github_refs import github_pull

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "github_pull-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)


def one():
    return github_pull("42")


value = one()
out.write_text(str(value) + "\n", encoding="utf-8")

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({
    "pull": value.pull,
    "class": value.r_class,
    "median_ms": statistics.median(elapsed),
}, separators=(",", ":")))
