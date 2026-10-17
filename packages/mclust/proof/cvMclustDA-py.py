import statistics
import subprocess
import sys
import time
from io import StringIO
import csv

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
from boot.rng import set_seed
from mclust.mclust_da import mclust_da
from mclust.cv_mclust_da import cv_mclust_da


def _iris():
    r = subprocess.run(
        [
            "R",
            "--slave",
            "-e",
            "suppressPackageStartupMessages(library(datasets)); write.csv(iris[,1:4], stdout(), row.names=FALSE)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    reader = csv.reader(StringIO(r.stdout))
    next(reader)
    x = np.array([[float(row[i]) for i in range(4)] for row in reader])
    class_ = subprocess.run(
        [
            "R",
            "--slave",
            "-e",
            "suppressPackageStartupMessages(library(datasets)); cat(as.character(iris$Species), sep='\\n')",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip().split("\n")
    return x, class_


def one():
    set_seed(42)
    x, class_ = _iris()
    fit = mclust_da(x, class_, model_type="EDDA", model_names="EEE", verbose=False)
    set_seed(42)
    cv = cv_mclust_da(fit, nfold=10, verbose=False)
    level_order = list(fit["prop"].keys())
    cl_map = {lev: i + 1 for i, lev in enumerate(level_order)}
    cl_num = np.array([cl_map[str(v)] for v in cv["classification"]], dtype=float)
    return [
        cv["ce"],
        cv["se.ce"],
        cv["brier"],
        cv["se.brier"],
        *cl_num.tolist(),
        *cv["z"].reshape(-1, order="F").tolist(),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
