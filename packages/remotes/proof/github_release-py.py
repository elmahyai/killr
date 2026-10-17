import json
import statistics
import time
from pathlib import Path

from remotes.github_refs import github_release

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "github_release-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)


def one():
    return github_release()


value = one()
out.write_text(str(value) + "\n", encoding="utf-8")

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

integer_na = (
    value.value is None
    and value.integer_na is True
    and value.na == "NA_integer_"
)

print(json.dumps({
    "integer_na": integer_na,
    "class": value.r_class,
    "median_ms": statistics.median(elapsed),
}, separators=(",", ":")))
