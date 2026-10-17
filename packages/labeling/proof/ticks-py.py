import json
import statistics
import time
from pathlib import Path

from labeling.ticks import (
    extended, gnuplot, heckbert, matplotlib, nelder, rpretty, sparks,
    thayer, wilkinson,
)

cases = {
    "heckbert": (8.1, 14.1, 4), "wilkinson": (8.1, 14.1, 4),
    "extended": (8.1, 14.1, 4), "nelder": (8.1, 14.1, 4),
    "rpretty": (8.1, 14.1, 6), "matplotlib": (8.1, 14.1, 4),
    "gnuplot": (8.1, 14.1, 4), "sparks": (8.1, 14.1, 4),
    "thayer": (8.1, 14.1, 4),
}
one, times = {}, {}
for name, args in cases.items():
    fn = globals()[name]
    one[name] = fn(*args)
    samples = []
    for _ in range(20):
        started = time.perf_counter()
        fn(*args)
        samples.append((time.perf_counter() - started) * 1000)
    times[name] = statistics.median(samples)
Path("packages/labeling/proof/p-results.json").write_text(
    json.dumps({"values": one, "times": times})
)
print("Python results written")
