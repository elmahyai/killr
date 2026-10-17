import json
import math
import statistics
import time
from pathlib import Path

from magrittr._fseq import FSeq
from magrittr.fseq import functions

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

fseq = FSeq([math.sqrt, math.log])


def one():
    return functions(fseq)


fns = one()
value = fns[1](fns[0](16))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
(out / "functions-python.txt").write_text("functions(fseq) returns 2 functions.\n")
