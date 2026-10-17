"""Kernel density and discrete histograms for MCMC output.

Translated from coda 0.19-4.1 ``densplot`` in ``R/output.R``.
The Gaussian curve is R's ``density``: linear binning on the first half of
a doubled grid, then a kernel FFT. Matplotlib draws the panels.
"""

from __future__ import annotations

import math
import sys

import matplotlib.pyplot as plt
import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import _nvar_mcmc, is_mcmc_list
from coda.niter import niter
from coda.varnames import varnames

_MISSING = object()
_EPS = sys.float_info.epsilon
_DBL_MIN = sys.float_info.min
_DBL_MAX = sys.float_info.max
_ROUNDING_EPS = 1e-10


def densplot(
    x,
    show_obs=True,
    bwf=_MISSING,
    ylim=_MISSING,
    xlab=_MISSING,
    ylab="",
    type="l",
    main=_MISSING,
    right=True,
    draw=True,
    **kwargs,
):
    """Density estimate for each variable in an MCMC chain or chain list.

    A variable that is integer-valued, constant, or has bandwidth 0 is drawn
    as a histogram. A sample bounded at 0, or inside [0, 1], is reflected
    before the Gaussian kernel is applied.
    """
    del kwargs
    matrix = _as_matrix(x)
    n_var = _nvar(x)
    n_iter = int(niter(x))
    names = varnames(x, allow_null=True)
    panels = []
    xlab_missing = xlab is _MISSING
    ylim_missing = ylim is _MISSING
    main_missing = main is _MISSING
    bwf_fn = None if bwf is _MISSING else bwf
    xlab_value = "" if xlab_missing else xlab
    ylim_par = None
    ylim_par_set = False

    for index in range(n_var):
        column = np.asarray(matrix[:, index], dtype=np.float64).reshape(-1)
        if bwf_fn is None:
            bwf_fn = _default_bwf
        bw = float(bwf_fn(column))
        if main_missing:
            if names is None:
                main_par = ""
            else:
                main_par = f"Density of {names[index]}"
        else:
            main_par = main

        discrete = _is_discrete(column, bw)
        if discrete:
            if xlab_missing:
                xlab_value = ""
                xlab_missing = False
            if ylim_missing:
                ylim_par = None
                ylim_par_set = True
            elif not ylim_par_set:
                raise NameError("object 'ylim.par' not found")
            breaks = _pretty_discrete(column, right)
            edges, density = _histogram_density(column, breaks, right=right)
            panels.append(
                {
                    "kind": "histogram",
                    "bw": bw,
                    "breaks": edges,
                    "density": density,
                    "xlab": xlab_value,
                    "ylab": ylab,
                    "main": main_par,
                    "ylim": ylim_par,
                    "right": right,
                }
            )
        else:
            scale, sample = _reflect(column, bw)
            curve_x, curve_y, dens_bw = _density(sample, bw)
            curve_x, curve_y = _clip_scale(scale, curve_x, curve_y)
            if ylim_missing:
                ylim_par = None
            else:
                ylim_par = ylim
            ylim_par_set = True
            if xlab_missing:
                xlab_par = f"N = {n_iter}  Bandwidth = {_format_c(dens_bw)}"
            else:
                xlab_par = xlab_value
            rug = None
            if show_obs and curve_y.size:
                rug_height = float(np.max(curve_y) / 100.0)
                rug = column[:n_iter]
            else:
                rug_height = float("nan")
                rug = np.array([], dtype=np.float64)
            panels.append(
                {
                    "kind": "density",
                    "bw": bw,
                    "dens_bw": dens_bw,
                    "x": curve_x,
                    "y": curve_y,
                    "rug": rug,
                    "rug_height": rug_height,
                    "xlab": xlab_par,
                    "ylab": ylab,
                    "main": main_par,
                    "ylim": ylim_par,
                    "type": type,
                }
            )

    result = {"panels": panels, "show_obs": show_obs}
    if draw:
        result["figure"] = _draw(result)
    return result


def proof_values(result):
    """Flatten bandwidths, grids, and histogram densities for an R check."""
    values = []
    for panel in result["panels"]:
        if panel["kind"] == "density":
            values.append(0.0)
            values.append(float(panel["bw"]))
            values.append(float(panel["dens_bw"]))
            values.append(float(panel["rug_height"]))
            rug = np.asarray(panel["rug"], dtype=np.float64).reshape(-1)
            values.append(float(rug.size))
            values.extend(float(item) for item in rug)
            grid_x = np.asarray(panel["x"], dtype=np.float64).reshape(-1)
            grid_y = np.asarray(panel["y"], dtype=np.float64).reshape(-1)
            values.append(float(grid_x.size))
            values.extend(float(item) for item in grid_x)
            values.append(float(grid_y.size))
            values.extend(float(item) for item in grid_y)
        else:
            values.append(1.0)
            values.append(float(panel["bw"]))
            edges = np.asarray(panel["breaks"], dtype=np.float64).reshape(-1)
            density = np.asarray(panel["density"], dtype=np.float64).reshape(-1)
            values.append(float(edges.size))
            values.extend(float(item) for item in edges)
            values.append(float(density.size))
            values.extend(float(item) for item in density)
    return values


def _draw(result):
    panels = result["panels"]
    n_var = len(panels)
    fig, axes = plt.subplots(n_var, 1, figsize=(7, 2.6 * n_var), squeeze=False)
    for index, panel in enumerate(panels):
        ax = axes[index, 0]
        if panel["kind"] == "density":
            ax.plot(panel["x"], panel["y"], color="black", linewidth=1.0)
            if panel["rug"].size:
                ax.vlines(
                    panel["rug"],
                    0.0,
                    panel["rug_height"],
                    colors="black",
                    linewidth=0.6,
                )
            finite_y = np.asarray(panel["y"], dtype=np.float64)
            finite_y = finite_y[np.isfinite(finite_y)]
            if panel["ylim"] is None and finite_y.size:
                ax.set_ylim(0.0, float(np.max(finite_y)) * 1.04)
            elif panel["ylim"] is not None:
                ax.set_ylim(panel["ylim"])
        else:
            edges = np.asarray(panel["breaks"], dtype=np.float64)
            heights = np.asarray(panel["density"], dtype=np.float64)
            widths = np.diff(edges)
            ax.bar(
                edges[:-1],
                heights,
                width=widths,
                align="edge",
                color="#d9d9d9",
                edgecolor="black",
                linewidth=0.6,
            )
            ax.set_xticks(edges)
            if panel["ylim"] is not None:
                ax.set_ylim(panel["ylim"])
        ax.set_xlabel(panel["xlab"])
        ax.set_ylabel(panel["ylab"])
        if panel["main"]:
            ax.set_title(panel["main"])
    fig.tight_layout()
    return fig


def _as_matrix(x):
    if is_mcmc(x):
        return _chain_matrix(x)
    if is_mcmc_list(x):
        return np.vstack([_chain_matrix(chain) for chain in x.chains])
    raise TypeError("densplot expects an mcmc or mcmc.list object")


def _chain_matrix(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _nvar(x):
    if is_mcmc(x):
        return _nvar_mcmc(x)
    if is_mcmc_list(x):
        return _nvar_mcmc(x.chains[0])
    return None


def _default_bwf(x):
    sample = np.asarray(x, dtype=np.float64).reshape(-1)
    sample = sample[~np.isnan(sample)]
    n = sample.size
    if n == 0:
        return float("nan")
    sd = float(np.std(sample, ddof=1)) if n > 1 else float("nan")
    q75, q25 = np.quantile(sample, [0.75, 0.25], method="linear")
    iqr = float(q75 - q25)
    return 1.06 * min(sd, iqr / 1.34) * n**-0.2


def _is_discrete(y, bw):
    if y.size == 0 or not np.all(np.isfinite(y)):
        return False
    integer_valued = float(np.max(np.abs(y - np.floor(y)))) == 0.0
    return bool(integer_valued or bw == 0.0 or np.unique(y).size == 1)


def _reflect(y, bw):
    if np.max(y) <= 1 and (1 - np.max(y)) < 2 * bw and np.min(y) >= 0 and np.min(y) < 2 * bw:
        return "proportion", np.concatenate((y, -y, 2 - y))
    if np.min(y) >= 0 and np.min(y) < 2 * bw:
        return "positive", np.concatenate((y, -y))
    return "open", y


def _clip_scale(scale, grid_x, grid_y):
    if scale == "proportion":
        keep = (grid_x >= 0) & (grid_x <= 1)
        return grid_x[keep], 3 * grid_y[keep]
    if scale == "positive":
        keep = grid_x >= 0
        return grid_x[keep], 2 * grid_y[keep]
    return grid_x, grid_y


def _density(x, bw, n=512, cut=3.0, ext=4.0):
    sample = np.asarray(x, dtype=np.float64).reshape(-1)
    if np.any(np.isnan(sample)):
        raise ValueError("'x' contains missing values")
    original_n = sample.size
    finite = np.isfinite(sample)
    sample = sample[finite]
    nx = sample.size
    if nx < 1:
        raise ValueError("no finite observations")
    if not np.isfinite(bw) or bw <= 0:
        raise ValueError("'bw' is not positive.")
    weights = np.full(nx, 1.0 / nx)
    tot_mass = nx / original_n
    n_user = n
    n = max(n, 512)
    if n > 512:
        n = 2 ** int(math.ceil(math.log2(n)))
    from_ = float(np.min(sample) - cut * bw)
    to = float(np.max(sample) + cut * bw)
    lo = from_ - ext * bw
    up = to + ext * bw
    binned = np.zeros(2 * n, dtype=np.float64)
    binned[:n] = _bin_dist(sample, weights, lo, up, n) * tot_mass
    factor = (2 * n - 1) / (n - 1)
    kords = np.linspace(0.0, factor * (up - lo), 2 * n)
    kords[n + 1 :] = -kords[n - 1 : 0 : -1]
    inv = 1.0 / (bw * math.sqrt(2.0 * math.pi))
    kernel = inv * np.exp(-0.5 * (kords / bw) ** 2)
    # R's inverse FFT is n times NumPy's ifft, and density divides by that n.
    transformed = np.fft.ifft(np.fft.fft(binned) * np.conj(np.fft.fft(kernel)))
    half = np.maximum(0.0, np.real(transformed)[:n])
    xords = np.linspace(lo, up, n)
    grid_x = np.linspace(from_, to, n_user)
    grid_y = np.interp(grid_x, xords, half)
    return grid_x, grid_y, float(bw)


def _bin_dist(x, weights, lo, up, n):
    y = np.zeros(n, dtype=np.float64)
    xdelta = (up - lo) / (n - 1)
    xpos = (x - lo) / xdelta
    ix = np.floor(xpos).astype(np.int64)
    fx = xpos - ix
    finite = np.isfinite(x)
    middle = finite & (ix >= 0) & (ix <= n - 2)
    if np.any(middle):
        np.add.at(y, ix[middle], (1.0 - fx[middle]) * weights[middle])
        np.add.at(y, ix[middle] + 1, fx[middle] * weights[middle])
    left = finite & (ix == -1)
    if np.any(left):
        y[0] += float(np.sum(fx[left] * weights[left]))
    right = finite & (ix == n - 1)
    if np.any(right):
        y[n - 1] += float(np.sum((1.0 - fx[right]) * weights[right]))
    return y


def _pretty_discrete(y, right):
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    ybreaks = _pretty(y, n=_nclass_sturges(y))
    seen = []
    marks = set()
    for value in y.tolist():
        if value not in marks:
            marks.add(value)
            seen.append(value)
    if len(seen) == 1:
        return ybreaks
    if len(ybreaks) > len(seen):
        ybreaks = sorted(seen)
    nb = len(ybreaks)
    ybreaks = [float(item) for item in ybreaks]
    if right:
        if float(np.max(y)) < ybreaks[nb - 1]:
            ybreaks[nb - 1] = float(np.max(y))
        if float(np.min(y)) > ybreaks[0]:
            ybreaks[0] = float(np.min(y) - 1)
        elif float(np.min(y)) == ybreaks[0]:
            ybreaks = [ybreaks[0] - 1.0, *ybreaks]
    else:
        if float(np.min(y)) > ybreaks[0]:
            ybreaks[0] = float(np.min(y))
        if float(np.max(y)) < ybreaks[nb - 1]:
            ybreaks[nb - 1] = float(np.max(y) + 1)
        elif float(np.max(y)) == ybreaks[nb - 1]:
            ybreaks = [ybreaks[nb - 1] + 1.0, *ybreaks]
    return ybreaks


def _histogram_density(x, breaks, right=True, include_lowest=True, fuzz=1e-7):
    sample = np.asarray(x, dtype=np.float64).reshape(-1)
    sample = sample[np.isfinite(sample)]
    edges = np.array(sorted(float(item) for item in breaks), dtype=np.float64)
    n = sample.size
    n_breaks = edges.size
    widths = np.diff(edges)
    if n_breaks > 5:
        diddle = fuzz * float(np.median(widths))
    elif n_breaks <= 3:
        diddle = fuzz * float(np.max(sample) - np.min(sample))
    else:
        positive = widths[widths > 0]
        diddle = fuzz * float(np.min(positive))
    if right:
        fuzz_vec = np.concatenate(
            (
                np.array([-diddle if include_lowest else diddle]),
                np.full(n_breaks - 1, diddle),
            )
        )
    else:
        fuzz_vec = np.concatenate(
            (
                np.full(n_breaks - 1, -diddle),
                np.array([diddle if include_lowest else -diddle]),
            )
        )
    fuzzy = edges + fuzz_vec
    counts = np.zeros(n_breaks - 1, dtype=np.float64)
    if right:
        indexes = np.searchsorted(fuzzy, sample, side="left") - 1
    else:
        indexes = np.searchsorted(fuzzy, sample, side="right") - 1
    if np.any(indexes < 0) or np.any(indexes >= n_breaks - 1):
        raise ValueError("some 'x' not counted; maybe 'breaks' do not span range of 'x'")
    np.add.at(counts, indexes, 1.0)
    density = counts / (n * widths)
    return edges, density


def _nclass_sturges(x):
    return int(math.ceil(math.log2(len(x)) + 1.0))


def _format_c(value):
    """R ``formatC`` with the default ``g`` format and 4 digits."""
    return format(float(value), ".4g")


def _pretty(x, n=5, min_n=None, shrink_sml=0.75, high_u_bias=1.5, u5_bias=None, eps_correct=0, f_min=2**-20):
    finite = [float(v) for v in np.asarray(x, dtype=np.float64).reshape(-1) if math.isfinite(float(v))]
    if not finite:
        return []
    if min_n is None:
        min_n = int(n) // 3
    if u5_bias is None:
        u5_bias = 0.5 + 1.5 * high_u_bias
    lo, up, ndiv, _unit = _r_pretty(
        min(finite),
        max(finite),
        int(n),
        int(min_n),
        float(shrink_sml),
        (float(high_u_bias), float(u5_bias), float(f_min)),
        int(eps_correct),
        True,
    )
    breaks = _seq_length(lo, up, ndiv + 1)
    if not eps_correct and ndiv:
        delta = abs(up - lo) / ndiv
        breaks = [0.0 if abs(v) < 1e-14 * delta else v for v in breaks]
    return breaks


def _seq_length(from_, to, length_out):
    length_out = int(length_out)
    if length_out == 1:
        return [float(from_)]
    if from_ == to:
        return [float(from_)] * length_out
    n1 = length_out - 1
    step = (to - from_) / n1
    middle = [from_ + i * step for i in range(1, length_out - 1)]
    return [float(from_), *[float(v) for v in middle], float(to)]


def _r_pretty(lo, up, ndiv, min_n, shrink_sml, high_u_fact, eps_correction, return_bounds):
    h, h5, f_min = high_u_fact
    lo_in = lo
    up_in = up
    span = up_in - lo_in
    if span == 0 and up_in == 0:
        cell = 1.0
        small = True
    else:
        cell = max(abs(lo_in), abs(up_in))
        unit_bound = 1 / (1 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1 + h5)
        unit_bound = (1 + unit_bound) * max(1, ndiv) * _EPS
        small = span < cell * unit_bound * 3
    if small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= shrink_sml
        if min_n > 1:
            cell /= min_n
    else:
        cell = span
        if math.isfinite(span):
            if ndiv > 1:
                cell /= ndiv
        elif ndiv >= 2:
            cell = up_in / ndiv - lo_in / ndiv
    smallest = f_min * _DBL_MIN
    if smallest == 0:
        smallest = _DBL_MIN
    if cell < smallest:
        cell = smallest
    elif cell > _DBL_MAX / 1.25:
        cell = _DBL_MAX / 1.25
    base = 10.0 ** math.floor(math.log10(cell))
    unit = base
    candidate = 2 * base
    if candidate - cell < h * (cell - unit):
        unit = candidate
        candidate = 5 * base
        if candidate - cell < h5 * (cell - unit):
            unit = candidate
            candidate = 10 * base
            if candidate - cell < h * (cell - unit):
                unit = candidate
    ns = math.floor(lo_in / unit + _ROUNDING_EPS)
    nu = math.ceil(up_in / unit - _ROUNDING_EPS)
    if eps_correction and (eps_correction > 1 or not small):
        lo = lo * (1 - _EPS) if lo_in != 0 else -_DBL_MIN
        up = up * (1 + _EPS) if up_in != 0 else _DBL_MIN
    while ns * unit > lo + _ROUNDING_EPS * unit:
        ns -= 1
    while not math.isfinite(ns * unit):
        ns += 1
    while nu * unit < up - _ROUNDING_EPS * unit:
        nu += 1
    while not math.isfinite(nu * unit):
        nu -= 1
    intervals = int(0.5 + nu - ns)
    if intervals < min_n:
        extra = min_n - intervals
        if lo_in == 0 and ns == 0 and up_in != 0:
            nu += extra
        elif up_in == 0 and nu == 0 and lo_in != 0:
            ns -= extra
        elif ns >= 0:
            nu += extra // 2
            ns -= extra // 2 + extra % 2
        else:
            ns -= extra // 2
            nu += extra // 2 + extra % 2
        ndiv = min_n
    else:
        ndiv = intervals
    if return_bounds:
        if ns * unit < lo:
            lo = ns * unit
        if nu * unit > up:
            up = nu * unit
    else:
        lo = ns
        up = nu
    return lo, up, ndiv, unit
