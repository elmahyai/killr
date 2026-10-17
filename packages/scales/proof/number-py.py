import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scales.number import number

SHORT = {"": 0.0, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def one():
    return number(
        [12345.67, -8.2, 0, None, float("inf"), float("-inf"), 2.5e5, 1.5e6],
        big_mark=",",
        prefix="$",
        style_negative="parens",
        scale_cut=SHORT,
    )


def shown(value):
    return "NA" if value is None else value


out = Path(__file__).resolve().parents[1] / "docs" / "output" / "number-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
example = one()
out.write_text(
    "number(c(12345.67, -8.2, 0, NA, Inf, -Inf, 2.5e5, 1.5e6), "
    'big.mark = ",", prefix = "$", style_negative = "parens", '
    "scale_cut = cut_short_scale()) returns "
    + ", ".join(shown(value) for value in example)
    + ".\n",
    encoding="utf-8",
)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
