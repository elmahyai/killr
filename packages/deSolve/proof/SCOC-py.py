import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")

from scoc import scocder_py

from deSolve.SCOC import SCOC

Flux = [
    [1, 0.654],
    [11, 0.167],
    [21, 0.060],
    [41, 0.070],
    [73, 0.277],
    [83, 0.186],
    [93, 0.140],
    [103, 0.255],
    [113, 0.231],
    [123, 0.309],
    [133, 1.127],
    [143, 1.923],
    [153, 1.091],
    [163, 1.001],
    [173, 1.691],
    [183, 1.404],
    [194, 1.226],
    [204, 0.767],
    [214, 0.893],
    [224, 0.737],
    [234, 0.772],
    [244, 0.726],
    [254, 0.624],
    [264, 0.439],
    [274, 0.168],
    [284, 0.280],
    [294, 0.202],
    [304, 0.193],
    [315, 0.286],
    [325, 0.599],
    [335, 1.889],
    [345, 0.996],
    [355, 0.681],
    [365, 1.135],
]
parms = {"k": 0.01}

pts = [
    (0.01, 63.00301, 0.654),
    (0.01, 34.3997631, 0.2205),
    (0.01, 72.98281, 1.135),
    (0.02, 10.0, 0.5),
    (0.005, 100.0, 0.0),
]

value = []
for k, y, depo in pts:
    ydot, mineralisation, depo_out = scocder_py(k, y, depo)
    value.extend([ydot, mineralisation, depo_out])

SCOC(list(range(1, 366)), parms=parms, Flux=Flux)

elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    SCOC(list(range(1, 366)), parms=parms, Flux=Flux)
    elapsed.append(time.perf_counter() - t0)

print(
    json.dumps(
        {
            "value": value,
            "median_ms": statistics.median(elapsed) * 1000,
        }
    )
)
