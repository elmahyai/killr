
import json
import statistics
import sys
import time

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/randomForest",
    "/home/ahmed/killr_projects/killr/packages/boot",
]
from boot.rng import set_seed
from randomForest import (
    class_center, combine, get_tree, grow, importance, mdsplot, partial_plot,
    predict, random_forest, rf_impute, rf_news, rfcv, treesize, tune_rf,
    var_imp_plot, var_used,
)

y = [1.2, 0.4, 2.1, 1.7, 0.2, 3.3, 2.8, 0.9, 1.1, 4.0, 0.5, 2.2, 1.8, 3.1, 0.7, 2.6, 1.4, 0.3, 3.6, 2.0]
x = [[(r + 20 * c + 1) / 7 for c in range(3)] for r in range(20)]
newx = [[2 / 7, 15 / 7, 30 / 7], [9 / 7, 22 / 7, 41 / 7]]
xc = [[(r + 16 * c + 1) / 5 for c in range(3)] for r in range(16)]
yc = ["b"] * 4 + ["a"] * 4 + ["b"] * 4 + ["a"] * 4

def columns(rows):
    rows = [list(row) for row in rows]
    return [float(row[col]) for col in range(len(rows[0])) for row in rows]

def clean(values):
    return [-1.0 if v != v else float(v) for v in values]

def as_rows(table):
    if hasattr(table, "tolist"):
        table = table.tolist()
    if table and isinstance(table[0], (list, tuple)):
        return columns(table)
    return [float(v) for v in table]

def codes(labels):
    level = {"a": 1.0, "b": 2.0}
    return [-1.0 if label is None else float(level[label]) for label in labels]

def reg():
    set_seed(2)
    return random_forest(x, y, ntree=3, mtry=2, nodesize=5, importance=True)

def one():
    fit = reg()
    return [float(v) for v in treesize(fit)] + [float(v) for v in treesize(fit, terminal=False)]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
