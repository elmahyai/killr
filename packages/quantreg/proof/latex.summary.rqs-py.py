import statistics
import time
import numpy as np
from quantreg.latex import latex_summary_rqs

x = [{"tau": .5, "coefficients": np.array([[1.2, .1, .03], [2.3, .2, .04]]),
      "names": ["a", "b"]}]
def one():
    return latex_summary_rqs(x, caption="Demo", file="/tmp/summary")
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter(); one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(one(), end="")
print(f"\n{statistics.median(elapsed):.17g}")
