import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/knitr")
from knitr.all_patterns import all_patterns


def one():
    return all_patterns


def rows(value):
    return [
        [lang, name, pattern]
        for lang, comps in value.items()
        for name, pattern in comps.items()
    ]


value = one()
text = (
    "all_patterns$rnw chunk.begin is "
    + value["rnw"]["chunk.begin"]
    + " and all_patterns$html header.begin is "
    + value["html"]["header.begin"]
    + "; str(all_patterns) is a list of "
    + str(len(value))
    + ".\n"
)
with open(
    "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/all_patterns-python.txt",
    "w",
    encoding="utf-8",
) as handle:
    handle.write(text)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": rows(value), "median_ms": statistics.median(elapsed)}))
