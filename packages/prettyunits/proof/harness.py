"""Shared proof harness for the Python side of prettyunits 1.2.0.

Each proof script calls run_proof(name, one). one() returns the Python result
for its case. One untimed call is made, then 20 timed calls with
time.perf_counter(). The median in milliseconds and the encoded result go to
docs/output/<name>-python.txt. The encoding matches proof/harness.R.
"""

import json
import math
import statistics
import sys
import time
from pathlib import Path

PROOF_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = PROOF_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

ERROR = "__error__"


def try_val(fn, *args, **kwargs):
    """Call fn; return the shared error marker when it raises."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        return ERROR


def enc(x):
    """Encode None, bool, number, string, list, and dict as JSON text."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        value = float(x)
        if math.isnan(value):
            return '{"special":"NaN"}'
        if math.isinf(value):
            return '{"special":"Inf"}' if value > 0 else '{"special":"-Inf"}'
        return repr(value)
    if isinstance(x, str):
        return json.dumps(x, ensure_ascii=True)
    if isinstance(x, dict):
        return "{" + ",".join(json.dumps(k) + ":" + enc(v) for k, v in x.items()) + "}"
    if isinstance(x, (list, tuple)):
        return "[" + ",".join(enc(v) for v in x) + "]"
    raise TypeError(f"cannot encode {type(x).__name__}")


def run_proof(name, one):
    value = one()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append(time.perf_counter() - started)
    median_ms = statistics.median(elapsed) * 1000
    out = PACKAGE_ROOT / "docs" / "output" / f"{name}-python.txt"
    text = f"median_ms {median_ms:.17g}\nresult {enc(value)}\n"
    out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return value
