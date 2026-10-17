import math
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass.gamma_dispersion import gamma_glm
from mass.gamma_shape import gamma_shape


def one():
    u = [5, 10, 15, 20, 30, 40, 60, 80, 100]
    clotting = {
        "u": u,
        "lot1": [118, 58, 42, 35, 27, 25, 21, 19, 18],
        "log(u)": [math.log(v) for v in u],
    }
    clot1 = gamma_glm("lot1 ~ log(u)", clotting)
    gs = gamma_shape(clot1)
    return [gs.alpha, gs.SE]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join("%.17g" % item for item in value))
print("%.17g" % statistics.median(elapsed))
