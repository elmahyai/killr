import json
import statistics
import time

from pillar.extent import new_ornament


def one():
    ornament = new_ornament(["abc", "de"], align="right")
    return {
        "text": str(ornament),
        "format5": ornament.format(width=5),
        "align": ornament.align,
        "width": ornament.width,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
