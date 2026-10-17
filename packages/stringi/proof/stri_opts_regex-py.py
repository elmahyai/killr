import json
import statistics
import time
from pathlib import Path

from stringi.opts import stri_opts_regex

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_opts_regex-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "stri_opts_regex(case_insensitive = TRUE) returns case_insensitive TRUE.\n",
    encoding="utf-8",
)


def pairs(opts):
    return [[key, value] for key, value in opts.items()]


def one():
    return [
        pairs(stri_opts_regex()),
        pairs(
            stri_opts_regex(
                case_insensitive=True,
                dot_all=True,
                multi_line=True,
                time_limit=5,
                stack_limit=9,
            )
        ),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, separators=(",", ":")))
