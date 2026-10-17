import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root.parent / "Formula"))
sys.path.insert(0, str(_root.parent / "nlme"))

from mass.glmm_pql import coef_model_struct, fixef, fitted, glmmPQL

_CASE = json.loads(
    Path(__file__).with_name("glmmPQL-bacteria.json").read_text(encoding="utf-8")
)


def _bacteria_data():
    return {
        "y": _CASE["y"],
        "week": _CASE["week"],
        "trt": {"levels": _CASE["trt_levels"], "values": _CASE["trt"]},
        "ID": _CASE["ID"],
    }


def one():
    fit = glmmPQL(
        "y ~ trt + I(week > 2)",
        "~ 1 | ID",
        family="binomial",
        data=_bacteria_data(),
        verbose=False,
    )
    return np.concatenate(
        [
            fixef(fit),
            np.array([fit.sigma, coef_model_struct(fit)["reStruct.ID"]], dtype=float),
            fitted(fit),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
