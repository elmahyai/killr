
import json
import math
import statistics
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.simplefilter("ignore")
import numpy as np
from boot.rng import set_seed
from tseries import *
from tseries.datasets import ice_river

NOISE = [-0.5910311025843684, 0.026594369016167005, -1.516553097081865, -1.3626533492958086, 1.1784891560316197, -0.9341513196733652, 1.3236056462120183, 0.6249177899447136, -0.04572295570609473, -1.0041205756722797, -0.8284332366639579, -0.34835172517298096, -1.538293397087049, -0.2555652454649533, -1.1499450327075535, 0.012326967679467856, -0.2229695407476216, 0.8877716479113029, -0.5921552798767458, -0.655718118580886, -0.6825176222150191, -0.015858192728274358, -0.4426047853550452, 0.3525574994488161, 0.07317058229140316, 0.0071588003806459044, -0.1876001106022523, -0.76570064552539, -0.2210568207449584, -0.9835885874701957, -1.1042840421509679, -0.9381502141783641, 0.678624244182574, -1.5774978652948257, -0.8699384582256414, 0.484677045357101, -0.18605269864439059, 1.5455547001836638, -0.6113800701281997, -0.3477564873363454, -1.6365163055394207, 0.020381440100037087, 0.8917426801678406, -0.8727496832522508, 0.8900508298394778, -0.3438743461293478, -2.186781368328002, 0.8800581814920434, 0.7238565561464254, 0.21985268026050242]

def cell(value):
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, float):
        if value != value:
            return "NaN"
        return format(value, ".17g")
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)

def join(values):
    return ",".join(cell(value) for value in np.ravel(values))

def series_text(obj):
    values = np.asarray(obj.values, float)
    finite = values[np.isfinite(values)]
    names = ",".join(obj.names)
    return "|".join([
        str(values.size),
        cell(obj.start),
        cell(obj.end),
        cell(obj.frequency),
        names,
        cell(float(finite[0])),
        cell(float(finite[-1])),
        str(int(values.size - finite.size)),
    ])

def stamps():
    text = ("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00")
    return [datetime.strptime(item, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() for item in text]

def one():
    text = write_irts(irts(stamps(), [1/3, 1.23, 10]), "/tmp/tseries-write-irts-py.txt")
    return text.strip().replace("\n", "|")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print(statistics.median(elapsed))
