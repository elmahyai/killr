import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.io import write_zoo
from zoo.series import Zoo

z = Zoo(
    np.array([[1.5, 2.25], [3.5, 4.75], [5.25, 6.125]], dtype=float),
    np.array([1.0, 2.0, 3.0]),
)
z.columns = ["a", "b"]
path = tempfile.mktemp()

def one():
    write_zoo(z, path)
    return Path(path).read_text()

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
