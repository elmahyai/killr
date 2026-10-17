
import json
import math
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/rpart", "/home/ahmed/killr_projects/killr/packages/boot"]
from boot.rng import set_seed
from rpart import (
    meanvar, na_rpart, path_rpart, plotcp, post, printcp, prune, prune_rpart,
    rpart, rpart_exp, rsq_rpart, snip_rpart, xpred_rpart,
)

y30 = [1.2, 0.4, 2.1, 1.7, 0.2, 3.3, 2.8, 0.9, 1.1, 4.0,
       0.5, 2.2, 1.8, 3.1, 0.7, 2.6, 1.4, 0.3, 3.6, 2.0,
       5.1, 0.8, 4.4, 1.5, 6.2, 2.9, 0.6, 3.8, 1.9, 4.7]
x1 = [(i + 1) / 3 for i in range(30)]
x1[4] = float("nan")
data30 = {
    "y": y30,
    "x1": x1,
    "x2": [5,1,8,2,9,3,7,4,6,2, 1,8,3,9,4,7,2,6,5,1, 9,3,8,2,7,4,6,1,5,3],
    "x3": [(30 - i) / 4 for i in range(30)],
}
ctrl30 = dict(minsplit=8, minbucket=3, cp=0.01, xval=5, maxdepth=10)

def fit30():
    set_seed(1)
    return rpart("y ~ .", data30, control=ctrl30)

def fit12():
    set_seed(11)
    return rpart(
        "y ~ .",
        {"y": [1,2,1.2, 5,4.5,5.5, 8,9,7.5, 3,3.2,2.8],
         "x1": [1,2,3, 6,7,8, 12,13,14, 4,5,9],
         "x2": [2,2,1, 0,1,0, 5,4,6, 3,3,2]},
        weights=[1,1,2, 1,3,1, 2,1,1, 1,1,4],
        control=dict(minsplit=4, minbucket=2, cp=0.001, xval=4, maxdepth=6),
    )

def finite(values):
    return [float(v) for v in values if math.isfinite(float(v))]

def columns(rows):
    return [float(row[col]) for col in range(len(rows[0])) for row in rows]

def one():
    sn = snip_rpart(fit30(), [2])
    return [row["yval"] for row in sn.frame] + list(sn.where)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
