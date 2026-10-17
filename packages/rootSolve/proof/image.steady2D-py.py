import statistics
import time
import matplotlib.pyplot as plt
import numpy as np
from rootSolve import image_steady2d, steady_2d

def g2(t, y, p):
    grid = np.asarray(y.values, dtype=float).reshape((3, 3), order="F")
    change = np.zeros_like(grid)
    for row in range(3):
        for col in range(3):
            left = 0.0 if row == 0 else grid[row - 1, col]
            right = 1.0 if row == 2 else grid[row + 1, col]
            down = 0.0 if col == 0 else grid[row, col - 1]
            up = 0.0 if col == 2 else grid[row, col + 1]
            change[row, col] = left + right + down + up - 4 * grid[row, col]
    return [change.reshape(-1, order="F")]

out = steady_2d([0.2] * 9, func=g2, dimens=(3, 3), nspec=1)

def one():
    drawn = image_steady2d(out, which=1)
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
