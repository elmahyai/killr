import statistics
import time
from pathlib import Path

import numpy as np

from _mclust_dr_fit_fixture import load_dr
from mclust.dr_predict import predict_MclustDR

P = Path(__file__).parent


def one():
    dr = load_dr()
    p = predict_MclustDR(dr, dim=(1, 2), newdata=dr["x"][:6])
    return np.r_[p["density"], p["z"].ravel(order="F"), p["uncertainty"], np.argmax(p["z"], axis=1) + 1]


if __name__ == "__main__":
    v = one()
    t = []
    for _ in range(20):
        s = time.perf_counter()
        one()
        t.append((time.perf_counter() - s) * 1000)
    expected = np.loadtxt(P / "predict.MclustDR-r-values.txt")
    d = float(np.max(np.abs(v - expected)))
    r_ms = float((P / "predict.MclustDR-r-ms.txt").read_text())
    print(f"matches {'true' if d <= 1e-8 else 'false'}")
    print(f"max_abs_diff {d:.17g}")
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {statistics.median(t):.17g}")
    print(f"speedup {r_ms/statistics.median(t):.17g}")
