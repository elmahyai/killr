"""Proof: locfit (formula front end) against R locfit 1.5-9.12.

F1: y ~ x with ev at 25 points. F2: y ~ x1 + x2, product kernel, ev = data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.locfit import locfit  # noqa: E402

DATA = {"type": "data"}


def main():
    d = L.inputs()
    x1, y1, x2, y2, xev1 = d["x1"], d["y1"], d["x2"], d["y2"], d["xev1"]
    df1 = {"x": x1.reshape(-1), "y": y1}
    df2 = {"x1": x2[:, 0], "x2": x2[:, 1], "y": y2}
    cases = {
        "F1": lambda: locfit("y ~ x", data=df1, alpha=0.7, deg=2, kern="tricube",
                             kt="sph", ev=xev1),
        "F2": lambda: locfit("y ~ x1 + x2", data=df2, alpha=0.5, deg=1, kern="tricube",
                             kt="prod", ev=DATA),
    }
    diffs = {}
    for case, call in cases.items():
        out = call()
        want = L.ref(f"locfit_{case}_coef")
        got = out["eva"]
        diffs[f"{case}_eva(coef,nlx,t0,lik,h)"] = L.max_diff(got, want[:, : got.shape[1]])
        mine = [out["dp"][k] for k in ("lk", "df1", "df2", "rv", "rsc")]
        diffs[f"{case}_dp(lk,df1,df2,rv,rsc)"] = L.max_diff(mine, L.ref_vec(f"locfit_{case}_dp"))
        L.save(f"locfit_{case}_eva", got)
    ms = L.timed_ms(cases["F1"])
    ok = L.finish("locfit", diffs, ms)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
