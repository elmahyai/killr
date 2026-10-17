import sys

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.radau import radau


def robertson(t, y, parms):
    dy1 = -0.04 * y[0] + 1e4 * y[1] * y[2]
    dy2 = 0.04 * y[0] - 1e4 * y[1] * y[2] - 3e7 * y[1] ** 2
    dy3 = 3e7 * y[1] ** 2
    return [[dy1, dy2, dy3]]


print(radau([1.0, 0.0, 0.0], [0.0, 10.0, 20.0, 30.0, 40.0], robertson, None))
