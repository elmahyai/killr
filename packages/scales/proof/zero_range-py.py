import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scales.bounds import zero_range

_EPS = sys.float_info.epsilon
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "zero_range-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
examples = [
    zero_range([1, 1 + _EPS]),
    zero_range([1, 1 + 99 * _EPS]),
    zero_range([1, 1 + 1001 * _EPS]),
    zero_range([1, 1 + 2 * _EPS], tol=_EPS),
    zero_range([100000 * 1, 100000 * (1 + _EPS)]),
    zero_range([100000 * 1, 100000 * (1 + 1001 * _EPS)]),
    zero_range([0.00001 * 1, 0.00001 * (1 + _EPS)]),
    zero_range([0.00001 * 1, 0.00001 * (1 + 1001 * _EPS)]),
    zero_range([1, None]),
    zero_range([1, float("nan")]),
    zero_range([1, float("inf")]),
    zero_range([float("-inf"), float("inf")]),
    zero_range([float("inf"), float("inf")]),
]
out.write_text("\n".join(repr(value) for value in examples) + "\n", encoding="utf-8")


def one():
    return zero_range([1, 1 + 1001 * _EPS])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
