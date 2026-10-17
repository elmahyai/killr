"""Python proof for hexpolygon(). Run from the repository root after hexpolygon_r.R:

    .venv/bin/python packages/hexbin/proof/hexpolygon_py.py

The R side records the vertices that grid.polygon() or polygon() would receive. The Python side
compares the returned vertex lists. Timing is for the geometry only, with no drawing.
"""

import math

from _proof_common import OUT_DIR, Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.hexcoords import hexcoords  # noqa: E402
from hexbin.hexpolygon import hexpolygon  # noqa: E402

NAME = "hexpolygon"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)
    x3 = [0.0, 1.0, 2.5]
    y3 = [0.0, 0.5, -1.0]

    r1 = hexpolygon(x3, y3, hexC=hexcoords(0.3, n=1))
    rep.num(ref, "case1.x", r1["x"])
    rep.num(ref, "case1.y", r1["y"])
    rep.num(ref, "case1.id", r1["id_lengths"])

    r2 = hexpolygon(x3, y3, hexC=hexcoords(0.3, 0.2, n=1))
    rep.num(ref, "case2.x", r2["x"])
    rep.num(ref, "case2.y", r2["y"])
    rep.num(ref, "case2.id", r2["id_lengths"])

    r3 = hexpolygon(x3, y3, hexC=hexcoords(dx=0.2, dy=0.15, n=1, sep=math.nan))
    rep.num(ref, "case3.x", r3["x"])
    rep.num(ref, "case3.y", r3["y"])

    r4 = hexpolygon(x3, y3, dx=0.25)
    rep.num(ref, "case4.x", r4["x"])
    rep.num(ref, "case4.y", r4["y"])
    rep.num(ref, "case4.id", r4["id_lengths"])

    px, py = points_fixed(2000)
    py_median = time_median(lambda: hexpolygon(px, py, dx=0.1))
    ok = rep.write(
        r_timing(ref),
        py_median,
        extra=["  timed call: hexpolygon on 2000 points, dx = 0.1, geometry only (no drawing)"],
    )

    # The drawn figure: the case-4 hexagons, drawn with Matplotlib.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 3))
    hexpolygon(x3, y3, dx=0.25, ax=ax, facecolor="none", edgecolor="black")
    ax.plot(x3, y3, "k.")
    ax.set_aspect("equal")
    ax.set_title("hexpolygon, dx = 0.25 (hexbin 1.28.6 geometry)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "hexpolygon-py.svg")
    plt.close(fig)
    print(f"wrote {OUT_DIR / 'hexpolygon-py.svg'}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
