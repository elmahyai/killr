import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")

from mass.addterm import glm
from mass.stepaic import stepAIC


def one():
    data = {
        "y": [5, 3, 8, 2, 6, 4],
        "x1": [0, 1, 1, 0, 1, 0],
        "x2": [1, 0, 1, 0, 0, 1],
        "x3": [0, 0, 1, 1, 1, 0],
    }
    m0 = glm("y ~ x1 + x2 + x3", data, family="poisson")
    result = stepAIC(
        m0,
        scope={"upper": "~x1 + x2 + x3", "lower": "~x1"},
        direction="both",
        trace=0,
    )
    out = [result.deviance, float(result.rank)]
    cols = ("Df", "Deviance", "Resid. Df", "Resid. Dev", "AIC")
    for col in cols:
        for row in result.anova.rows:
            out.append(float(result.anova.values[(row, col)]))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
