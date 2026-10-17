"""Proof: locfit.matrix against R locfit 1.5-9.12 on the weighted, based fit C."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.locfit_raw import locfit_raw  # noqa: E402
from locfit_translated.locfit_matrix import locfit_matrix  # noqa: E402


def main():
    d = L.inputs()
    fit = locfit_raw(d["x1"], d["y1"], weights=d["w1"], base=d["b1"], alpha=0.5, deg=2,
                     kern="tricube", kt="sph", ev={"type": "data"})
    mm = locfit_matrix(fit, None)
    diffs = {
        "x": L.max_diff(mm["x"], L.ref("matrix_M1_x")),
        "y": L.max_diff(mm["y"], L.ref_vec("matrix_M1_y")),
        "w": L.max_diff(mm["w"], L.ref_vec("matrix_M1_w")),
        "sc": L.max_diff(mm["sc"], L.ref_vec("matrix_M1_sc")),
        "ce": L.max_diff(mm["ce"], L.ref_vec("matrix_M1_ce")),
        "base": L.max_diff(mm["base"], L.ref_vec("matrix_M1_base")),
    }
    for key in ("x", "y", "w", "sc", "ce", "base"):
        L.save(f"locfit_matrix_{key}", mm[key])
    ms = L.timed_ms(lambda: locfit_matrix(fit, None))
    ok = L.finish("locfit_matrix", diffs, ms)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
