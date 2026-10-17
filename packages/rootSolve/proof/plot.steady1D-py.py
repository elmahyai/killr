import statistics
import time
import matplotlib.pyplot as plt
from rootSolve import plot_steady1d, steady_1d

def g(t, y, p):
    n = len(y)
    rate = [0.0] * n
    rate[0] = y[1] - y[0]
    for i in range(1, n - 1):
        rate[i] = y[i - 1] - 2 * y[i] + y[i + 1]
    rate[-1] = 1 - y[-1]
    return [rate]

out = steady_1d([0.2] * 5, func=g, nspec=1)

def one():
    drawn = plot_steady1d(out)
    coords = list(drawn.coordinates[0]['y'])
    plt.close(drawn.figure)
    return coords

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
