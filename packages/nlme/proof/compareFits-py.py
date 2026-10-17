import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.comparefits import NamedMatrix, compareFits

_R_LOAD = """
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(nlme))
data(Orthodont, package = "nlme")
fm1 <- lmList(Orthodont)
fm2 <- lme(fm1)
m1 <- coef(fm1)
m2 <- coef(fm2)
cat(jsonlite::toJSON(list(
  rn = rownames(m1),
  cn = colnames(m1),
  m1 = unname(as.vector(m1)),
  m2 = unname(as.vector(m2))
), auto_unbox = FALSE, digits = 17))
"""


def _orthodont_tables():
    payload = subprocess.run(
        ["Rscript", "-e", _R_LOAD],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(payload)
    nrow = len(data["rn"])
    ncol = len(data["cn"])

    def _coef_matrix(raw):
        if isinstance(raw, list) and raw and isinstance(raw[0], list):
            return np.column_stack([np.asarray(column, dtype=np.float64) for column in raw])
        return np.array(raw, dtype=np.float64).reshape(nrow, ncol, order="F")

    m1 = _coef_matrix(data["m1"])
    m2 = _coef_matrix(data["m2"])
    names = tuple(str(name) for name in data["rn"])
    cols = tuple(str(name) for name in data["cn"])
    return NamedMatrix(m1, names, cols), NamedMatrix(m2, names, cols)


OBJECT1, OBJECT2 = _orthodont_tables()


def one():
    values = np.asfortranarray(compareFits(OBJECT1, OBJECT2).values, dtype=np.float64)
    return values.ravel(order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
