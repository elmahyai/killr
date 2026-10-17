import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from minpacklm.nlsLM import nlsLM
from minpacklm.wfct import puromycin_treated


def pack_fit(fit):
    weights = fit.weights
    if weights is None:
        weight_vals = []
    else:
        weight_vals = [float(item) for item in np.ravel(weights)]
    coef = [float(fit.coefficients[name]) for name in fit.coefficients]
    return [
        *coef,
        *[float(item) for item in np.ravel(fit.residuals)],
        *[float(item) for item in np.ravel(fit.fitted)],
        float(fit.deviance),
        1.0 if fit.conv_info["isConv"] else 0.0,
        float(fit.conv_info["finIter"]),
        float(fit.conv_info["finTol"]),
        float(fit.conv_info["stopCode"]),
        float(len(weight_vals)),
        *weight_vals,
    ]


def one():
    treated = puromycin_treated()
    plain = nlsLM(
        "rate ~ Vm * conc / (K + conc)",
        data=treated,
        start={"Vm": 200.0, "K": 0.05},
    )
    weighted = nlsLM(
        "rate ~ Vm * conc / (K + conc)",
        data=treated,
        start={"Vm": 200.0, "K": 0.05},
        weights=1.0 / treated["rate"],
    )
    x = np.arange(1, 11, dtype=float)
    y = 2.0 * x + 3.0
    frame = {"x": x, "y": y}
    start = {"a": 0.12345, "b": 0.54321}
    linear = nlsLM("y ~ a + b * x", data=frame, start=start)
    part = nlsLM("y ~ a + b * x", data=frame, start=start, subset=np.arange(1, 6))
    if not plain.conv_info["isConv"]:
        raise AssertionError(plain.conv_info)
    if plain.conv_info["stopMessage"] != "Relative error in the sum of squares is at most `ftol'.":
        raise AssertionError(plain.conv_info["stopMessage"])
    packed = []
    for fit in (plain, weighted, linear, part):
        packed.extend(pack_fit(fit))
    return packed


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (
        ",".join("%.17g" % float(part) for part in value),
        statistics.median(elapsed),
    )
)
