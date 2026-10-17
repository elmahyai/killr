"""Translation of ``plot.MclustBootstrap`` (mclust 6.1.3, R/bootstrap.R).

The R function draws one histogram per mixture parameter (``what = "pro"``,
``"mean"`` or ``"var"``) with ``hist``, then the estimate as a vertical line
(``abline``), and the percentile interval and the bootstrap average as a
segment and a square (``lines`` and ``points``). Each panel here is recorded
as the same primitives R draws, with the same numbers, in call order. When a
Matplotlib figure is given, the panels are drawn on it with Matplotlib. When
it is not, only the data is computed, which is the timed path.

The axis limits follow R's ``plot.window``: each limit is widened by 4% on
both sides (``xaxs = "r"``, ``yaxs = "r"``), so the Matplotlib axes show the
same ``par("usr")`` as R.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from mclust._plot_common import nclass_sturges, pretty, usr_r
from mclust.bootstrap_family import summary_MclustBootstrap

__all__ = ["plot_MclustBootstrap", "nclass_numpy", "nclass_fd", "r_hist"]

_WHAT = ("pro", "mean", "var")
_PCH_SQUARE = 15


def _get(x: Any, key: str, default: Any = None) -> Any:
    try:
        return x[key]
    except (KeyError, TypeError):
        return default


def _match_what(what: Any) -> str:
    """``match.arg(what, c("pro", "mean", "var"))``."""
    if isinstance(what, (list, tuple)):
        if tuple(what) == _WHAT:
            return "pro"
        if len(what) != 1:
            raise ValueError("'what' must be of length 1")
        what = what[0]
    name = str(what)
    if name in _WHAT:
        return name
    hits = [w for w in _WHAT if name and w.startswith(name)]
    if len(hits) == 1:
        return hits[0]
    raise ValueError("'arg' should be one of 'pro', 'mean', 'var'")


def _signif(v: float, digits: int) -> float:
    """``signif(v, digits)`` for one double."""
    if not math.isfinite(v) or v == 0.0:
        return v
    return float(f"{v:.{digits - 1}e}")


def nclass_fd(x: Any, digits: int = 5) -> int:
    """``grDevices::nclass.FD(x, digits)``: Freedman-Diaconis classes."""
    values = np.asarray(x, dtype=float).ravel()
    rounded = np.array([_signif(v, digits) for v in values], dtype=float)
    q = np.quantile(rounded, [0.25, 0.75])
    h = 2.0 * float(q[1] - q[0])
    if h == 0:
        xs = np.sort(rounded)
        al = 0.25
        al_min = 1.0 / 512.0
        while h == 0:
            al = al / 2.0
            if al < al_min:
                break
            qa = np.quantile(xs, [al, 1.0 - al])
            h = float(qa[1] - qa[0]) / (1.0 - 2.0 * al)
    if h == 0:
        h = 3.5 * math.sqrt(float(np.var(values, ddof=1)))
    if h > 0:
        return int(math.ceil((float(values.max() - values.min()) / h) * len(values) ** (1.0 / 3.0)))
    return 1


def nclass_numpy(x: Any) -> int:
    """``mclust:::nclass.numpy``: the larger of the Sturges and Freedman-Diaconis counts."""
    values = np.asarray(x, dtype=float).ravel()
    return max(nclass_sturges(values), nclass_fd(values))


def r_hist(values: Any, breaks: Any = None) -> dict[str, Any]:
    """``graphics::hist(values, breaks, plot = FALSE)`` with ``right = TRUE``, ``include.lowest = TRUE``.

    ``breaks`` is ``None`` (or NA) for ``nclass.numpy``, a number for ``pretty``
    breaks, or a vector of break points. Returns the breaks, counts, density,
    mids, ``equidist``, and ``y``, the heights R draws (counts when equidist,
    density otherwise).
    """
    x = np.asarray(values, dtype=float).ravel()
    x = x[np.isfinite(x)]
    n = x.size
    lo_hi = np.array([x.min(), x.max()])
    if breaks is None or (np.ndim(breaks) == 0 and np.isnan(float(breaks))):
        brks = pretty(lo_hi, n=nclass_numpy(x), min_n=1)
        use_br = True
    elif np.ndim(breaks) == 0:
        brks = pretty(lo_hi, n=int(breaks), min_n=1)
        use_br = False
    else:
        brks = np.sort(np.asarray(breaks, dtype=float).ravel())
        use_br = True
    nB = brks.size
    h = np.diff(brks)
    # R: diddle <- fuzz * if (nB > 5) median(h) else if (nB <= 3) diff(range(x)).
    # For 4 or 5 edges the median is what R's fuzz gives (checked against R).
    if nB <= 3:
        diddle = 1e-7 * float(x.max() - x.min())
    else:
        diddle = 1e-7 * float(np.median(h))
    fuzz = np.concatenate(([-diddle], np.full(nB - 1, diddle)))
    fuzzy = brks + fuzz
    j = np.searchsorted(fuzzy, x, side="left")
    inside = (j >= 1) & (j <= nB - 1)
    counts = np.bincount(j[inside] - 1, minlength=nB - 1).astype(float)
    density = counts / (n * h)
    mids = 0.5 * (brks[:-1] + brks[1:])
    equidist = (not use_br) or (float(h.max() - h.min()) < 1e-7 * float(h.mean()))
    y = counts if equidist else density
    return {"breaks": brks, "counts": counts, "density": density, "mids": mids,
            "equidist": equidist, "y": y, "n": n}


def _fmt_nums(values: Any) -> list[float]:
    return [float(v) for v in np.asarray(values, dtype=float).ravel()]


def plot_MclustBootstrap(
    x: Any,
    what: Any = "pro",
    show_parest: bool = True,
    show_confint: bool = True,
    hist_col: str = "grey",
    hist_border: str = "lightgrey",
    breaks: Any = None,
    col: str = "forestgreen",
    lwd: float = 2,
    lty: float = 3,
    xlab: str | None = None,
    xlim: Any = None,
    ylim: Any = None,
    varnames: Any = None,
    conf_level: float = 0.95,
    fig: Any = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Port of ``plot.MclustBootstrap``.

    Returns one dict per panel with the recorded primitives (``records``) and
    the axis limits (``usr``). ``records`` is a list of ``(tag, fields)``:
    ``XLAB``, ``HIST``, ``USR``, ``ABLINE``, ``LINES``, ``POINTS``, as R's
    ``hist``, ``abline``, ``lines`` and ``points`` receive them. When ``fig``
    is given, each panel is drawn on its own axes of ``fig``, in a grid of at
    most three columns.
    """
    what = _match_what(what)
    if breaks is not None and np.ndim(breaks) != 0:
        # R: if(is.na(breaks)) ... fails on a vector in R 4.5 ("the condition has length > 1")
        raise ValueError("the condition has length > 1")
    par_ = x["parameters"]
    G = int(_get(x, "G"))
    boot_pro = np.asarray(_get(x, "pro"), dtype=float).reshape(-1, G)
    nboot = boot_pro.shape[0]
    boot_mean = np.asarray(_get(x, "mean"), dtype=float)
    d = boot_mean.shape[1]
    boot_mean = boot_mean.reshape(nboot, d, G)
    boot_var = np.asarray(_get(x, "variance"), dtype=float).reshape(nboot, d, d, G)
    par_pro = np.asarray(par_["pro"], dtype=float).reshape(G)
    par_mean = np.asarray(par_["mean"], dtype=float).reshape(d, G)
    par_var = np.asarray(par_["variance"], dtype=float).reshape(d, d, G)

    ci = ave = None
    if show_confint:
        ci = summary_MclustBootstrap(x, what="ci", conf_level=conf_level)
        ave = summary_MclustBootstrap(x, what="ave")

    panels: list[dict[str, Any]] = []

    def hist_boot(boot, stat, ci_vals, ave_val, lab, xlim_, ylim_):
        h = r_hist(boot, breaks)
        xl = xlim_ if xlim_ is not None else (h["breaks"][0], h["breaks"][-1])
        yl = ylim_ if ylim_ is not None else (min(0.0, float(h["y"].min())), max(0.0, float(h["y"].max())))
        usr = (*usr_r(xl), *usr_r(yl))
        recs: list[tuple[str, list[Any]]] = [
            ("XLAB", [lab]),
            ("HIST", [h["breaks"], h["counts"], h["density"], h["y"]]),
            ("USR", [np.asarray(usr)]),
        ]
        y0 = usr[2] / 2.0
        if show_parest:
            recs.append(("ABLINE", [np.asarray([stat]), [col], np.asarray([lwd]), np.asarray([lty])]))
        if show_confint:
            recs.append(("LINES", [np.asarray(ci_vals), np.asarray([y0, y0]), [col], np.asarray([lwd])]))
            recs.append(("POINTS", [np.asarray([ave_val]), np.asarray([y0]),
                                    np.asarray([_PCH_SQUARE]), [col]]))
        panels.append({"records": recs, "usr": usr, "hist": h, "stat": stat,
                       "ci": None if ci_vals is None else np.asarray(ci_vals),
                       "ave": ave_val, "y0": y0, "lab": lab})

    def label(j, k, kind):
        # R: ifelse(is.null(xlab), paste(...), xlab); paste() of NULL varnames gives ""
        if xlab is not None:
            return xlab
        if kind == "pro":
            return f"Mix. prop. for comp. {k + 1}"
        name = "" if varnames is None else str(varnames[j])
        stem = "mean for comp." if kind == "mean" else "var. for comp."
        return " ".join([name, stem, str(k + 1)])

    if what == "pro":
        pretty_pro = pretty(boot_pro, n=5, min_n=1)
        xl_all = (float(pretty_pro.min()), float(pretty_pro.max())) if xlim is None else tuple(sorted(xlim))
        for k in range(G):
            hist_boot(boot_pro[:, k], par_pro[k],
                      None if ci is None else ci["pro"][:, k],
                      None if ave is None else ave["pro"][k],
                      label(0, k, "pro"), xl_all, ylim)
    elif what == "mean":
        for j in range(d):
            if xlim is None:
                pm = pretty(boot_mean[:, j, :], n=5, min_n=1)
                xl = (float(pm.min()), float(pm.max()))
            else:
                xl = tuple(sorted(xlim))
            for k in range(G):
                hist_boot(boot_mean[:, j, k], par_mean[j, k],
                          None if ci is None else ci["mean"][:, j, k],
                          None if ave is None else ave["mean"][j, k],
                          label(j, k, "mean"), xl, ylim)
    else:
        for j in range(d):
            if xlim is None:
                pv = pretty(boot_var[:, j, j, :], n=5, min_n=1)
                xl = (float(pv.min()), float(pv.max()))
            else:
                xl = tuple(sorted(xlim))
            for k in range(G):
                hist_boot(boot_var[:, j, j, k], par_var[j, j, k],
                          None if ci is None else ci["variance"][:, j, k],
                          None if ave is None else ave["variance"][j, j, k],
                          label(j, k, "var"), xl, ylim)

    if fig is not None:
        _draw(fig, panels, hist_col, hist_border, col, lwd, lty, show_parest, show_confint)
    return panels


def _draw(fig: Any, panels: list[dict[str, Any]], hist_col: str, hist_border: str,
          col: str, lwd: float, lty: float, show_parest: bool, show_confint: bool) -> None:
    """Draw each panel on its own axes, in a grid of at most three columns."""
    fig.clear()
    n = len(panels)
    ncol = min(n, 3)
    nrow = int(math.ceil(n / ncol))
    linestyle = ":" if lty == 3 else "--" if lty == 2 else "-"
    for i, p in enumerate(panels):
        ax = fig.add_subplot(nrow, ncol, i + 1)
        h = p["hist"]
        b = h["breaks"]
        ax.bar(b[:-1], h["y"], width=np.diff(b), align="edge", color=hist_col,
               edgecolor=hist_border, linewidth=0.5)
        ax.set_xlim(p["usr"][0], p["usr"][1])
        ax.set_ylim(p["usr"][2], p["usr"][3])
        ax.set_xlabel(p["lab"])
        if show_parest:
            ax.axvline(p["stat"], color=col, linewidth=lwd, linestyle=linestyle)
        if show_confint:
            ax.plot(p["ci"], [p["y0"], p["y0"]], color=col, linewidth=lwd)
            ax.scatter([p["ave"]], [p["y0"]], marker="s", color=col)
    fig.tight_layout()
