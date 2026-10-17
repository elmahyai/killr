import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.gnls import gnls
from nlme.gnlscontrol import gnlsControl

x = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8]
y = [2.71, 2.35, 2.08, 1.84, 1.63, 1.45, 1.29, 1.16, 1.04, 0.93, 0.84, 0.76, 0.69, 0.63, 0.57, 0.52]


def one():
    fit = gnls(
        "y ~ a * exp(b * x)",
        {"x": x, "y": y},
        start={"a": 2.0, "b": -0.15},
        control=gnlsControl(apVar=False),
    )
    return [
        *fit.coefficients.tolist(),
        fit.sigma,
        fit.logLik,
        fit.numIter,
        *fit.fitted.tolist(),
        *fit.residuals.tolist(),
        *fit.varBeta.reshape(-1, order="F").tolist(),
    ]


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
