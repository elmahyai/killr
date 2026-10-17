import math
import statistics
import sys
import time
import urllib.error
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "zoo"))

import numpy as np
from tseries.finance import get_hist_quote

INSTRUMENT = "^GSPC"
START = "2020-01-02"
END = "2020-03-31"
OUT = ROOT / "docs" / "output" / "get.hist.quote-py.txt"
R_OUT = ROOT / "docs" / "output" / "get.hist.quote-r.txt"


def cell(value):
    value = float(value)
    if math.isnan(value):
        return "NaN"
    return format(value, ".17g")


def one():
    return get_hist_quote(INSTRUMENT, start=START, end=END, quiet=True)


def fetch_with_retries():
    attempts = 0
    while True:
        attempts += 1
        try:
            return one(), attempts
        except (urllib.error.URLError, RuntimeError) as error:
            network = isinstance(error, urllib.error.URLError)
            if not network or attempts > 3:
                return error, attempts
            time.sleep(30)


result, attempts = fetch_with_retries()
if isinstance(result, Exception):
    OUT.write_text("\n".join([
        "status: blocked",
        f"instrument: {INSTRUMENT} start: {START} end: {END}",
        f"attempts: {attempts}",
        f"error: {type(result).__name__}: {result}",
    ]) + "\n")
    print(f"blocked: {type(result).__name__}: {result} (attempts {attempts})")
    sys.exit(2)

values = np.asarray(result.data, dtype=float)
index = [str(date(1970, 1, 1) + timedelta(days=int(day))) for day in np.asarray(result.index, dtype=float)]

timed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    timed.append((time.perf_counter() - started) * 1000)
py_ms = statistics.median(timed)

lines = [
    "status: ok",
    f"nrow: {values.shape[0]}",
    f"colnames: {','.join(result.colnames)}",
    f"index: {','.join(str(day) for day in index)}",
    f"values: {','.join(cell(v) for v in values.ravel(order='F'))}",
    f"py_ms: {format(py_ms, '.17g')}",
]
OUT.write_text("\n".join(lines) + "\n")
print("\n".join(lines[:3]))

if R_OUT.exists() and "status: ok" in R_OUT.read_text():
    r_lines = dict(line.split(": ", 1) for line in R_OUT.read_text().splitlines() if ": " in line)
    r_values = np.asarray([float(v) for v in r_lines["values"].split(",")])
    r_index = r_lines["index"].split(",")
    same_index = r_index == index
    max_diff = float(np.nanmax(np.abs(r_values - values.ravel(order="F"))))
    matches = same_index and max_diff <= 1e-8
    r_ms = float(r_lines["r_ms"])
    print(f"matches: {matches} max_abs_diff: {max_diff} index_match: {same_index}")
    print(f"r_ms: {r_ms} translated_ms: {py_ms} speedup: {r_ms / py_ms}")
else:
    print("R reference output not ok; no comparison made")
