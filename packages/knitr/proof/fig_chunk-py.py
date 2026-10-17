import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/knitr")
from knitr.fig_chunk import fig_chunk, knitr_options, opts_chunk, opts_knit

opts_chunk.restore()
opts_knit.restore()
knitr_options.pop("knitr.sanitize.paths", None)


def one():
    return fig_chunk("foo", "png", [1, 2, 3, 4, 5])


value = one()
text = (
    'fig_chunk("foo", "png", 1:5) returns '
    + ", ".join(value)
    + ".\n"
)
with open(
    "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/fig_chunk-python.txt",
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
