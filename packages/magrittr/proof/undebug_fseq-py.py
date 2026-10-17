import json
import statistics
import time
from pathlib import Path

from magrittr._fseq import FSeq
from magrittr.fseq import _is_debugged, debug_fseq, undebug_fseq

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)


def first(value):
    return value


def second(value):
    return value


fseq = FSeq([first, second])
debug_fseq(fseq, 1)


def one():
    return undebug_fseq(fseq)


value = one()
if value is not None:
    raise RuntimeError("expected None")
if _is_debugged(first) or _is_debugged(second):
    raise RuntimeError("still marked")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
(out / "undebug_fseq-python.txt").write_text("undebug_fseq(fseq) returns None.\n")
