import json
import math
import statistics
import sys
import time
import warnings
import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/fracdiff")
warnings.simplefilter("ignore")
from fracdiff import *

def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value

def one():
    innov = [i / 10 for i in range(1, 61)]; return fracdiff_sim(60, d=0.2, innov=innov, start_innov=[], n_start=0, allow_0_nstart=True)['series']

value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
