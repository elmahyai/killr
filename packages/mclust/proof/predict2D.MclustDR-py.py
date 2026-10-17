import statistics
import time
from pathlib import Path

import numpy as np

from _mclust_dr_fit_fixture import load_dr
from mclust.dr_predict import predict2D_MclustDR

P = Path(__file__).parent


def one():
    p = predict2D_MclustDR(load_dr(), ngrid=5)
    return np.r_[
        p["x"],
        p["y"],
        p["density"].ravel(order="F"),
        p["z"].ravel(order="F"),
        p["uncertainty"].ravel(order="F"),
        np.asarray(p["classification"]).ravel(order="F").astype(int),
    ]


if __name__ == "__main__":
    v = one()
    ts = []
    for _ in range(20):
        s = time.perf_counter()
        one()
        ts.append((time.perf_counter() - s) * 1000)
    e = np.loadtxt(P / "predict2D.MclustDR-r-values.txt")
    d = float(np.max(np.abs(v - e)))
    r = float((P / "predict2D.MclustDR-r-ms.txt").read_text())
    m = statistics.median(ts)
    print(f"matches {'true' if d <= 1e-8 else 'false'}\nmax_abs_diff {d:.17g}\nr_ms {r:.17g}\ntranslated_ms {m:.17g}\nspeedup {r/m:.17g}")
