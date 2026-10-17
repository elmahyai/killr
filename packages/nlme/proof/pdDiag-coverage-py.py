from pathlib import Path
import json
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coverage_common import ROOT, emit, load_nlme, timed  # noqa: E402

load_nlme()
from nlme.glsapvar import ConLin  # noqa: E402
from nlme.initialize import Initialize  # noqa: E402
from nlme.logdet import logDet  # noqa: E402
from nlme.matrix_assign import pd_matrix_from_params  # noqa: E402
from nlme.recalc import recalc  # noqa: E402
from nlme.restruct import coef, load_pixel_csv, reStruct  # noqa: E402

# Same inputs as pdDiag-coverage-r.R: the Pixel model with the conLin captured from lme().
_FIXTURE = json.loads((ROOT / "proof" / "data" / "reStruct-pixel-conlin.json").read_text())
N = int(_FIXTURE["N"])
NCOL = int(_FIXTURE["ncol"])
CONLIN_XY = np.asarray(_FIXTURE["Xy"], dtype=np.float64).reshape(N, NCOL, order="F")
CONLIN_DIMS = _FIXTURE["dims"]
CONLIN_SIGMA = float(_FIXTURE["sigma"])
PIXEL = load_pixel_csv()


def conlin(logLik=0.0):
    return ConLin(Xy=CONLIN_XY.copy(), dims=CONLIN_DIMS, logLik=logLik, sigma=CONLIN_SIGMA)


def make_rs():
    return Initialize(
        reStruct({"Dog": "~day", "Side": "~1"}, pdClass="pdDiag", data=PIXEL),
        PIXEL,
        conLin=conlin(),
    )


def fingerprint(obj):
    parts = [float(v) for v in obj.settings]
    parts.extend(float(v) for v in obj.plen)
    for _, element in obj.blocks:
        parts.extend(float(v) for v in coef(element))
    for _, element in obj.blocks:
        mat = pd_matrix_from_params(element.pd_class, element.values, len(element.names))
        parts.extend(float(v) for v in np.ravel(mat, order="F"))
    return np.asarray(parts, dtype=np.float64)


def init_fn():
    return fingerprint(make_rs())


def logdet_fn():
    return np.asarray(logDet(make_rs()), dtype=np.float64)


def recalc_fn():
    r = recalc(make_rs(), conlin(logLik=0.5))
    return np.concatenate([np.ravel(r.Xy, order="F"), np.asarray([float(r.logLik)])])


emit(
    {
        "Initialize": timed(init_fn),
        "logDet": timed(logdet_fn),
        "recalc": timed(recalc_fn),
    }
)
