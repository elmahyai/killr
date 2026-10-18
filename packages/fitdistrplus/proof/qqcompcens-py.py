import pathlib
import sys
import time
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from fitdistrplus.qqcompcens import qqcompcens

left = np.array([-np.inf, 0, 1, 2, 4, 5.])
right = np.array([0, 1, 2, 4, 5, np.inf])
fit = {
    "estimate": {"mean": 2.2, "sd": 1.4},
    "distname": "norm",
    "censdata": {"left": left, "right": right},
}

def values():
    out = qqcompcens(fit, NPMLE_method="Turnbull.intervals")
    rect = out["rectangles"][0]
    return np.column_stack((out["left"], out["right"], out["p"],
                            rect["theoretical_left"], rect["theoretical_right"]))

one = values()
times = []
for _ in range(20):
    t0 = time.perf_counter()
    values()
    times.append(time.perf_counter() - t0)
outpath = pathlib.Path(__file__).parents[1] / "docs/output/qqcompcens-py-values.tsv"
np.savetxt(outpath, one, delimiter="\t")
print(f"translated_ms={np.median(times) * 1000:.9f}")
