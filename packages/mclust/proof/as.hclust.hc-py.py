import importlib.util, statistics, time
from pathlib import Path
import numpy as np
spec = importlib.util.spec_from_file_location("m", Path(__file__).parents[1] / "mclust" / "as_hclust.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
p = {"pairs": np.array([[-1, -3, -2], [2, 3, 4]]), "model": "EII"}
one = lambda: np.r_[m.as_hclust_hc(p, what="merge")["merge"].ravel(order="F"), m.as_hclust_hc(p, what="merge")["height"], m.as_hclust_hc(p, what="merge")["order"]]
value = one(); elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
print(*[f"{v:.17g}" for v in value]); print(f"{statistics.median(elapsed):.17g}")
