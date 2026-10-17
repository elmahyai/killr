import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust.icl_print import summary_mclust_icl

x = {"values": np.array([[10., 9.], [8., 7.]]),
     "G": ["1", "2"], "modelNames": ["EII", "VII"]}


def one():
    return summary_mclust_icl(x)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
reference = ["EII,1", "VII,1", "EII,2"]
matches = value["names"] == reference and np.allclose(
    value["values"], [10., 9., 8.], atol=1e-8, rtol=0
)
max_abs_diff = float(np.max(np.abs(value["values"] - [10., 9., 8.])))
output_path = Path(__file__).parents[1] / "docs" / "output" / "summary.mclustICL.txt"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text("\n".join(f"{name}={item:g}" for name, item in
                                zip(value["names"], value["values"])) + "\n")
print(f"matches {matches}\nmax_abs_diff {max_abs_diff:.17g}")
print(f"translated_ms {statistics.median(elapsed):.17g}")
