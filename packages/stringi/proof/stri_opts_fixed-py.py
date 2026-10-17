import json
import statistics
import time
from pathlib import Path

from stringi.opts import stri_opts_fixed

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_opts_fixed-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "stri_opts_fixed(overlap = TRUE) returns overlap TRUE.\n",
    encoding="utf-8",
)


def pairs(opts):
    return [[key, value] for key, value in opts.items()]


def one():
    return [
        pairs(stri_opts_fixed()),
        pairs(stri_opts_fixed(overlap=True)),
        pairs(stri_opts_fixed(case_insensitive=False, overlap=True)),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, separators=(",", ":")))
