import statistics
import time

from mass.addterm import addterm, glm


def one():
    data = {
        "y": [5, 3, 8, 2],
        "x1": [0, 1, 1, 0],
        "x2": [1, 0, 1, 0],
    }
    m0 = glm("y ~ x1", data, family="poisson")
    table = addterm(m0, "~ . + x2", test="Chisq")
    return table.as_matrix().reshape(-1)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
