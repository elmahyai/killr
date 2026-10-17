"""Plot several groups of points or lines: Python translation of R's multilines (ca 0.72).

R splits ``XY`` by ``group`` (in order of first appearance), sorts each group by
column ``sort`` when it is 1 or 2, and calls ``lines()`` for each group in
``which``. Colours come from ``palette()`` by default; ``which`` is 1-based as
in R. ``multilines_data`` returns the line records; ``multilines`` draws them.
"""

import numpy as np
import matplotlib.pyplot as plt

# R's default palette() in R >= 4.0
R_PALETTE = (
    "black", "#DF536B", "#61D04F", "#2297E6", "#28E2E5", "#CD0BBC", "#F5C710", "gray62",
)


def multilines_data(XY, group=None, which=None, sort=1, type="l", col=None, lwd=1):
    """Return one record per drawn group: x, y, type, col and lwd as R passes them."""
    xy = np.asarray(XY, dtype=float)
    if xy.ndim != 2 or xy.shape[1] != 2:
        raise ValueError("XY must have two columns")
    n = xy.shape[0]
    if group is None:
        group = [1] * n
    fact = [str(g) for g in group]  # as.character(group)
    index = {lev: k for k, lev in enumerate(dict.fromkeys(fact))}
    levels = list(index)
    nf = len(levels)
    codes = np.fromiter((index[f] for f in fact), dtype=np.intp, count=n)
    palette = list(R_PALETTE if col is None else col)
    widths = list(lwd) if isinstance(lwd, (list, tuple, np.ndarray)) else [lwd]
    which = list(range(1, nf + 1)) if which is None else list(which)

    records = []
    for i in which:
        if i < 1:
            raise ValueError("which must be 1-based group numbers")
        if i > nf:
            # R: fact[i] is NA, so subset() returns no rows and lines() draws nothing
            records.append({"x": np.empty(0), "y": np.empty(0), "type": type,
                            "col": None, "lwd": None})
            continue
        sub = xy[codes == i - 1]
        if sort in (1, 2):
            order = np.argsort(sub[:, sort - 1], kind="stable")
            sub = sub[order]
        # R's rep(col, out.length = nf) does not recycle (out.length is not a rep()
        # argument), so col[i] and lwd[i] index the given vectors; past the end, NA
        colour = palette[i - 1] if i - 1 < len(palette) else None
        width = widths[i - 1] if i - 1 < len(widths) else None
        records.append({
            "x": sub[:, 0], "y": sub[:, 1], "type": type,
            "col": colour, "lwd": width,
        })
    return records


def multilines(XY, group=None, which=None, sort=1, type="l", col=None, lwd=1, ax=None):
    """Draw the group lines on ``ax`` (default: the current axes) and return the records."""
    if ax is None:
        ax = plt.gca()
    records = multilines_data(XY, group=group, which=which, sort=sort, type=type,
                              col=col, lwd=lwd)
    for rec in records:
        if rec["col"] is None:
            continue
        if rec["type"] == "l":
            ax.plot(rec["x"], rec["y"], color=rec["col"], linewidth=rec["lwd"] or 1)
        elif rec["type"] == "p":
            ax.scatter(rec["x"], rec["y"], color=rec["col"])
        elif rec["type"] == "o":
            ax.plot(rec["x"], rec["y"], color=rec["col"], linewidth=rec["lwd"] or 1,
                    marker="o")
        else:
            raise NotImplementedError(f"lines type {rec['type']!r} is not translated")
    return records
