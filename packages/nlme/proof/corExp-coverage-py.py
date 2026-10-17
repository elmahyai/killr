from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coverage_common import emit, load_nlme, timed  # noqa: E402

load_nlme()
from nlme.corexp import corExp  # noqa: E402
from nlme.glsapvar import ConLin  # noqa: E402
from nlme.initialize import Initialize  # noqa: E402
from nlme.logdet import logDet  # noqa: E402
from nlme.recalc import recalc  # noqa: E402

# Same inputs as corExp-coverage-r.R.
DAT = {
    "Subject": ["a", "a", "a", "a", "b", "b", "b"],
    "x": [0.0, 1.0, 0.5, 2.0, 0.2, 1.4, 2.6],
    "y": [0.0, 0.0, 1.0, 0.5, 0.3, 1.1, 0.4],
}


def con():
    return ConLin(
        Xy=np.arange(1, 15, dtype=np.float64).reshape(7, 2, order="F"),
        dims={"N": 7, "p": 2},
        logLik=0.5,
    )


def make_a():
    return Initialize(corExp(3, form="~ x + y | Subject"), DAT)


def make_b():
    return Initialize(corExp([3, 0.2], form="~ x + y | Subject", nugget=True, metric="man"), DAT)


def init_fn():
    a, b = make_a(), make_b()
    return np.concatenate([np.ravel(a.value), np.ravel(b.value)])


def logdet_fn():
    a, b = make_a(), make_b()
    return np.asarray([logDet(a), logDet(b)], dtype=np.float64)


def recalc_fn():
    ra = recalc(make_a(), con())
    rb = recalc(make_b(), con())
    return np.concatenate(
        [
            np.ravel(ra.Xy, order="F"),
            np.asarray([float(ra.logLik)]),
            np.ravel(rb.Xy, order="F"),
            np.asarray([float(rb.logLik)]),
        ]
    )


emit(
    {
        "Initialize": timed(init_fn),
        "logDet": timed(logdet_fn),
        "recalc": timed(recalc_fn),
    }
)
