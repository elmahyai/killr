"""Python proof for hgridcent(). Run from the repository root after hgridcent_r.R:

    .venv/bin/python packages/hexbin/proof/hgridcent_py.py
"""

from _proof_common import Report, load_ref, r_timing, time_median  # noqa: E402

from hexbin.hgridcent import hgridcent  # noqa: E402

NAME = "hgridcent"


def record_grid(rep, ref, prefix, g):
    rep.num(ref, f"{prefix}.x", g["x"])
    rep.num(ref, f"{prefix}.y", g["y"])
    rep.num(ref, f"{prefix}.dimen", g["dimen"])
    rep.num(ref, f"{prefix}.dx", g["dx"])
    rep.num(ref, f"{prefix}.dy", g["dy"])


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)

    record_grid(rep, ref, "case1", hgridcent(30, (-5, 5), (-3, 3), 1))
    record_grid(rep, ref, "case2", hgridcent(12, (-5, 5), (-3, 3), 0.8, edge_add=2))
    record_grid(rep, ref, "case3", hgridcent(20, (-5, 5), (-3, 3), 1.2, edge_add=1))
    record_grid(rep, ref, "case4", hgridcent(7.5, (0, 9), (0, 4), 1))

    py_median = time_median(lambda: hgridcent(300, (-5, 5), (-3, 3), 1, edge_add=2))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
