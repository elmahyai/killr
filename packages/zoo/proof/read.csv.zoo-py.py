import datetime as dt
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.io import read_csv_zoo

def canon(z):
    origin = dt.date(1970, 1, 1)
    index = " ".join(format(float((value - origin).days), ".17g") for value in z.index)
    values = " ".join(format(float(value), ".17g") for value in np.asarray(z.data, dtype=float).ravel(order="F"))
    return "index " + index + "\nvalues " + values

path = tempfile.mktemp()
Path(path).write_text(
    "date,a,b\n"
    "2020-01-01,1.5,2.25\n"
    "2020-01-02,3.5,4.75\n"
    "2020-01-03,5.25,6.125\n"
)

def one():
    z = read_csv_zoo(path)
    return canon(z)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
