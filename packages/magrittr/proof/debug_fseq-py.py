import json
import statistics
import time
from pathlib import Path

from magrittr._fseq import FSeq
from magrittr.fseq import _is_debugged, debug_fseq

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)


def first(value):
    return value


def second(value):
    return value


def third(value):
    return value


fseq = FSeq([first, second, third])


def one():
    return debug_fseq(fseq, 2)


one()
value = float(
    _is_debugged(second) and not _is_debugged(first) and not _is_debugged(third)
)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
(out / "debug_fseq-python.txt").write_text("debug_fseq(fseq, 2) returns None.\n")
