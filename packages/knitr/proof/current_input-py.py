import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/knitr")
from knitr.current_input import current_input, knit_concord, opts_knit

knit_concord.restore()
opts_knit.restore()
knit_concord.set(infile="notes/report.Rmd")
opts_knit.set(**{"output.dir": "/work/out"})


def one():
    return current_input(dir=True)


value = one()
text = "current_input(dir = TRUE) returns " + value + ".\n"
with open(
    "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/current_input-python.txt",
    "w",
    encoding="utf-8",
) as handle:
    handle.write(text)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
