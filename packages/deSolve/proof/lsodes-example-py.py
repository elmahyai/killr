import sys

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.lsodes import lsodes


def logist(t, x, parms):
    r = parms["r"]
    k = parms["K"]
    return [r * x[0] * (1 - x[0] / k)]


out = lsodes(
    {"N": 0.1},
    list(range(0, 11, 2)),
    logist,
    {"r": 0.5, "K": 100.0},
    rtol=1e-8,
    atol=1e-8,
)
print(out)
