import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

import io
import sys

from pillar.glimpse import glimpse


def one():
    frame = DataFrame({"a": [1, 2, 3], "b": ["x", "yy", "zzz"], "c": [True, False, None]})
    buffer = io.StringIO()
    old = sys.stdout
    sys.stdout = buffer
    try:
        glimpse(frame, width=40)
    finally:
        sys.stdout = old
    text = buffer.getvalue()
    if text.endswith("\n"):
        text = text[:-1]
    return text

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
