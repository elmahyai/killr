import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corexp import corExp
from nlme.corgaus import corGaus
from nlme.corlin import corLin, initialize as initialize_lin
from nlme.corratio import corRatio, initialize as initialize_ratio
from nlme.corspher import corSpher, initialize as initialize_spher
from nlme.variogram import Variogram

DATA = {
    "x": [0.0, 1.0, 0.5, 2.0],
    "y": [0.0, 0.0, 1.0, 0.5],
}
OBS = np.array([1.2, 3.4, 2.2, 5.1])
X = np.array([0.0, 1.0, 0.5, 2.0])
DIST_DEFAULT = np.array([X[i] - X[j] for j in range(4) for i in range(j + 1, 4)])
DIST_DEFAULT = np.abs(DIST_DEFAULT)
GRID = np.linspace(0.0, 3.0, 7)


def _pack(frame):
    return np.concatenate([frame.variog, frame.dist])


def one():
    parts = [
        _pack(Variogram(OBS, DIST_DEFAULT)),
        _pack(Variogram(corExp(np.log(2.5), form="~ x + y", metric="eu"), distance=GRID)),
        _pack(
            Variogram(
                corExp(np.log([2.5, 0.2]), form="~ x + y", nugget=True, metric="eu"),
                distance=GRID,
            )
        ),
        _pack(Variogram(corGaus(1, form="~ x + y", metric="man"), distance=GRID)),
        _pack(Variogram(initialize_lin(corLin(2.5, form="~ x + y", metric="eu"), DATA))),
        _pack(
            Variogram(
                initialize_ratio(corRatio(1.8, form="~ x + y", metric="eu"), DATA),
                distance=GRID,
                sig2=2.0,
            )
        ),
        _pack(Variogram(initialize_spher(corSpher(2.5, form="~ x + y", metric="eu"), DATA), distance=GRID)),
    ]
    return np.concatenate(parts)


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
