"""Proof: locfit.raw against R locfit 1.5-9.12 (eva$coef and dp summaries).

Cases are the fits in locfit10_r.R: A 1-D data fit, B 1-D fit at 25 points,
C 1-D with weights and base, D 2-D product kernel. The default ev = rbox()
is not in the kernel; its raise is recorded as a note.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.locfit_raw import locfit_raw  # noqa: E402

DATA = {"type": "data"}


def main():
    d = L.inputs()
    x1, y1, w1, b1, xev1, x2, y2 = (d[k] for k in ("x1", "y1", "w1", "b1", "xev1", "x2", "y2"))
    cases = {
        "A": lambda: locfit_raw(x1, y1, alpha=0.7, deg=2, kern="tricube", kt="sph", ev=DATA),
        "B": lambda: locfit_raw(x1, y1, alpha=0.7, deg=2, kern="tricube", kt="sph", ev=xev1),
        "C": lambda: locfit_raw(x1, y1, weights=w1, base=b1, alpha=0.5, deg=2,
                                kern="tricube", kt="sph", ev=DATA),
        "D": lambda: locfit_raw(x2, y2, alpha=0.5, deg=1, kern="tricube", kt="prod", ev=DATA),
    }
    diffs = {}
    for case, call in cases.items():
        out = call()
        want = L.ref(f"raw_{case}_coef")
        got = out["eva"]
        assert got.shape[0] == want.shape[0], (got.shape, want.shape)
        # R's eva$coef has one trailing informational column that the kernel does not emit.
        diffs[f"{case}_eva(coef,nlx,t0,lik,h)"] = L.max_diff(got, want[:, : got.shape[1]])
        dp = L.ref_vec(f"raw_{case}_dp")
        mine = [out["dp"][k] for k in ("lk", "df1", "df2", "rv", "rsc")]
        diffs[f"{case}_dp(lk,df1,df2,rv,rsc)"] = L.max_diff(mine, dp)
        L.save(f"locfit_raw_{case}_eva", got)
    try:
        locfit_raw(x1, y1)
        note = "default ev=rbox(): ran (unexpected)"
    except NotImplementedError as exc:
        note = f"default ev=rbox(): not translated, {exc}"
    print("note:", note)
    ms = L.timed_ms(cases["A"])
    ok = L.finish("locfit_raw", diffs, ms)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
