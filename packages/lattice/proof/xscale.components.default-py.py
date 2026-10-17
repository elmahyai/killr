import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.xscale_components_default import xscale_components_default


def encode(comp):
    bottom = comp["bottom"]
    nums = [
        *comp["num.limit"],
        *bottom["ticks"]["at"],
        bottom["ticks"]["tck"],
        *bottom["labels"]["at"],
        1.0 if bottom["labels"]["check.overlap"] else 0.0,
        1.0 if comp["top"] is True else 0.0,
    ]
    return nums, bottom["labels"]["labels"]


def one():
    nums, labels = encode(xscale_components_default([0, 1]))
    return {"nums": nums, "labels": labels}


result = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": result["nums"],
            "labels": result["labels"],
            "median_ms": [statistics.median(elapsed)],
        }
    )
)
