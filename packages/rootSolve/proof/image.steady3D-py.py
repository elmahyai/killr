import statistics
import time
import matplotlib.pyplot as plt
from rootSolve import image_steady3d, steady_3d

def approach(t, y, p):
    return [[1.0 - value for value in y]]

out = steady_3d([0.0] * 8, func=approach, dimens=(2, 2, 2))

def one():
    drawn = image_steady3d(out, which=1)
    z = list(drawn.coordinates[0]['z'].ravel(order='F'))
    plt.close(drawn.figure)
    return z

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
