import statistics
import sys
import time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust import bic_family as module
x = {"values": np.array([[10., 9.], [8., 7.]]), "G": ["1", "2"], "modelNames": ["EII", "VII"]}
one = lambda: module.mclustModel(np.arange(1, 5).reshape(2, 2), x)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value["G"])
print(value["modelName"])
for item in value["bic"]:
    print(item)
print(f"{statistics.median(elapsed):.17g}")
