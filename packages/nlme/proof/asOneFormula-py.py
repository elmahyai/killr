import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.asoneformula import asOneFormula


def one():
    return str(
        asOneFormula(
            "y ~ x + z | g",
            ["~ w", "~ t * sin(2 * pi)"],
        )
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
