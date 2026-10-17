import statistics, sys, time
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1]))
from mclust import summary_mclust_bic as m
object_ = {"values": np.array([[-15.016671193134002]]), "G": ["1"], "modelNames": ["X"]}
one = lambda: m.summaryMclustBIC(object_, np.arange(1., 5.).reshape(-1, 1))
value = one(); elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
print("|".join(map(str, [value["modelName"], value["G"], value["n"], value["d"], value["bic"], value["loglik"], *value["classification"], *value["uncertainty"]])))
print(f"{statistics.median(elapsed):.17g}")
