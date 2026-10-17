import statistics
import sys
import time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust import bic_family as module
x = np.array([1., 2., 3., 4.])
one = lambda: module.mclustBIC(x, G=1, modelNames="E")
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"{value['values'][0, 0]:.17g}")
print(f"{statistics.median(elapsed):.17g}")
