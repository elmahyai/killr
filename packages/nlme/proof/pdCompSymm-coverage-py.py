from pathlib import Path
import json
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coverage_common import ROOT, emit, load_nlme, timed  # noqa: E402

load_nlme()
from nlme.glsapvar import ConLin  # noqa: E402
from nlme.initialize import Initialize  # noqa: E402
from nlme.logdet import logDet  # noqa: E402
from nlme.matrix_assign import pd_matrix_from_params  # noqa: E402
from nlme.recalc import recalc  # noqa: E402
from nlme.pdcompsymm import pdCompSymm  # noqa: E402
from nlme.restruct import _default_settings, _finalize_restruct, coef, load_pixel_csv, reStruct  # noqa: E402

# pdCompSymm is on the 2x2 Dog block only (R cannot initialize a 1x1 pdCompSymm block).
# Same inputs as pdCompSymm-coverage-r.R: the Pixel model with the conLin captured from lme().
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
    # reStruct(list(Dog = pdCompSymm(~day), Side = ~1)): reStruct's pdClass argument would apply
    # to both blocks, so the Dog element is built alone and swapped in, keeping the pdLogChol Side.
    base = reStruct({"Dog": "~day", "Side": "~1"}, data=PIXEL)
    dog = reStruct({"Dog": "~day"}, pdClass="pdCompSymm", data=PIXEL).blocks[0][1]
    blocks = [(name, dog if name == "Dog" else element) for name, element in base.blocks]
    rs = _finalize_restruct(blocks, _default_settings(False, [element for _, element in blocks]), None)
    return Initialize(rs, PIXEL, conLin=conlin())


def make_init_rs():
    # Initialized blocks as in the R proof: Dog = pdCompSymm(matrix(c(2, .6, .6, 2))), Side = logChol(4).
    template_dog = reStruct({"Dog": "~day"}, pdClass="pdCompSymm", data=PIXEL).blocks[0][1]
    template_side = reStruct({"Side": "~1"}, data=PIXEL).blocks[0][1]
    dog = replace(template_dog, values=np.asarray(pdCompSymm(np.array([[2.0, 0.6], [0.6, 2.0]]), form="~ day", data=PIXEL).values, dtype=np.float64))
    side = replace(template_side, values=np.array([np.log(2.0)], dtype=np.float64))
    # R reverses the block list, so Side comes first, as in R reStruct(list(Dog, Side)).
    blocks = [("Side", side), ("Dog", dog)]
    return _finalize_restruct(blocks, _default_settings(False, [dog, side]), None)


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
    rs = make_init_rs()
    return np.concatenate([[logDet(rs.blocks[0][1])], np.asarray(logDet(rs), dtype=np.float64)])


def recalc_fn():
    r = recalc(make_init_rs(), conlin(logLik=0.5))
    return np.concatenate([np.ravel(r.Xy, order="F"), np.asarray([float(r.logLik)])])


emit(
    {
        "Initialize": timed(init_fn),
        "logDet": timed(logdet_fn),
        "recalc": timed(recalc_fn),
    }
)
