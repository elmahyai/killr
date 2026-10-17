"""Bootstrap result helpers from mclust 6.1.3.

``MclustBootstrap`` is translated for all four resampling types. ``"bs"``
draws rows with R's ``sample`` (ported in ``boot.rng``) and refits each draw
with ``me``. ``"wlbs"`` draws Gamma weights with R's ``rgamma`` and refits with
``me_weighted``. ``"pb"`` simulates from the fit and refits with ``me``.
``"jk"`` leaves one row out per replicate. The result summaries and print
methods are deterministic and are implemented here for Python mapping-like
result objects.
"""

from __future__ import annotations

import math
import sys
import textwrap
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from mclust.estep import estep
from mclust.me import me
from mclust.mstep_loglik_icl import me_weighted
from mclust.print_mclust import summary_Mclust
from mclust.sim import sim

__all__ = [
    "MclustBootstrap",
    "print_MclustBootstrap",
    "summary_MclustBootstrap",
    "print_summary_MclustBootstrap",
    "print_mclustBootstrapLRT",
]


def _get(x: Any, key: str, default: Any = None) -> Any:
    return x.get(key, default) if isinstance(x, Mapping) else getattr(x, key, default)


def _boot_sample_int():
    """``boot.rng.sample_int``, the port of R's ``sample.int`` (Rejection sampling)."""
    try:
        from boot.rng import sample_int
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int
    return sample_int


def _nmath_rgamma():
    """R's ``rgamma(shape, scale)`` (nmath) on boot's Mersenne-Twister.

    The port lives in the extraDistr package (``extradistr._rgen``); it is
    loaded from the sibling folder, as ``_boot_sample_int`` loads ``boot``.
    """
    try:
        from extradistr._rgen import rgamma
    except ImportError:
        pkgs = Path(__file__).resolve().parents[2]
        for folder in ("boot", "extraDistr"):
            if str(pkgs / folder) not in sys.path:
                sys.path.insert(0, str(pkgs / folder))
        from extradistr._rgen import rgamma
    return rgamma


_TYPES = ("bs", "wlbs", "pb", "jk")


def _match_type(type_: Any) -> str:
    """``match.arg(type, c("bs", "wlbs", "pb", "jk"))`` after the nonpara/wlb rename."""
    if isinstance(type_, (list, tuple)):
        if tuple(type_) == _TYPES:
            return "bs"
        if len(type_) != 1:
            raise ValueError("'type' must be of length 1")
        type_ = type_[0]
    name = str(type_)
    if name in _TYPES:
        return name
    hits = [t for t in _TYPES if t.startswith(name)] if name else []
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"'arg' should be one of {', '.join(repr(t) for t in _TYPES)}")


def _refit(type_: str, b: int, n: int, data: np.ndarray, z: np.ndarray, model_name: Any,
           parameters: Any, alpha: float, sample_int: Any, rgamma: Any) -> dict[str, Any]:
    """One replicate of ``MclustBootstrap``. ``b`` is the 1-based replicate number."""
    if type_ == "bs":
        # R: idx <- sample(seq_len(n), size = n, replace = TRUE)
        idx = np.asarray(sample_int(n, n, replace=True), dtype=int) - 1
        return me(data[idx, :], model_name, z=z[idx, :], warn=False)
    if type_ == "wlbs":
        # R: w <- rgamma(n, shape = alpha, rate = 1); w <- w/max(w)
        w = np.array([rgamma(alpha, 1.0) for _ in range(n)], dtype=float)
        w = w / np.max(w)
        return me_weighted(data, model_name, z=z, weights=w, warn=False)
    if type_ == "pb":
        # R: obj$data <- sim(object)[,-1]; obj$z <- estep(obj$data, object)$z
        draws = np.asarray(sim(model_name, parameters, n), dtype=float)[:, 1:]
        zz = np.asarray(estep(draws, model_name, parameters)["z"], dtype=float)
        return me(draws, model_name, z=zz, warn=False)
    # jk: R: idx <- seq_len(n)[-b], leave one observation out
    idx = np.delete(np.arange(n), b - 1)
    return me(data[idx, :], model_name, z=z[idx, :], warn=False)


def MclustBootstrap(
    object_: Any,
    nboot: int = 999,
    type: str = "bs",
    alpha: float = 1,
    max_nonfit: int | None = None,
    verbose: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Port of ``MclustBootstrap`` (mclust 6.1.3, R/bootstrap.R).

    Types ``"bs"`` (nonparametric), ``"wlbs"`` (weighted likelihood), ``"pb"``
    (parametric) and ``"jk"`` (jackknife) are translated. Each replicate
    refits the model with ``me`` (``me_weighted`` for ``wlbs``) and keeps the
    mixing proportions, means and variances. A failed or ``NA`` refit is not
    counted and is added to ``nonfit``, up to ``max_nonfit``. The random
    stream is R's (``set.seed`` must be called first to match R).
    """
    del verbose, kwargs
    if type == "nonpara":
        type = "bs"
    if type == "wlb":
        type = "wlbs"
    type = _match_type(type)
    nboot = int(nboot)
    alpha = float(alpha)
    sample_int = _boot_sample_int()
    rgamma = _nmath_rgamma() if type == "wlbs" else None

    n = int(_get(object_, "n"))
    d = int(_get(object_, "d"))
    G = int(_get(object_, "G"))
    model_name = _get(object_, "modelName")
    data = np.asarray(_get(object_, "data"), dtype=float).reshape(n, d)
    z = np.asarray(_get(object_, "z"), dtype=float).reshape(n, G)

    # R: par <- summary(object)[c("pro", "mean", "variance")], then the d == 1 reshape.
    par = summary_Mclust(object_)
    par_pro = np.asarray(par["pro"], dtype=float).reshape(G)
    par_mean = np.asarray(par["mean"], dtype=float).reshape(d, G)
    par_variance = np.asarray(par["variance"], dtype=float).reshape(d, d, G)

    if type == "jk":
        nboot = n  # R: if(type == "jk") nboot <- n
    # R's max.nonfit = 10*nboot is a lazy default, read after the jk update above.
    if max_nonfit is None:
        max_nonfit = 10 * nboot

    pro_boot = np.full((nboot, G), np.nan)
    mean_boot = np.full((nboot, d, G), np.nan)
    var_boot = np.full((nboot, d, d, G), np.nan)

    raw_parameters = _get(object_, "parameters")

    b = 0
    nonfit = 0
    while b < nboot and nonfit < max_nonfit:
        b += 1
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mod = _refit(type, b, n, data, z, model_name, raw_parameters, alpha,
                             sample_int, rgamma)
        except Exception:  # R: try(do.call(...), silent = TRUE)
            mod = None
        loglik = None if mod is None else mod.get("loglik")
        if loglik is None or math.isnan(float(loglik)):
            if type != "jk":  # R: a failed jk replicate keeps its row index
                b -= 1
            nonfit += 1
            continue
        params = mod["parameters"]
        pro_boot[b - 1] = np.asarray(params["pro"], dtype=float).reshape(G)
        mean_boot[b - 1] = np.asarray(params["mean"], dtype=float).reshape(d, G)
        var_boot[b - 1] = np.asarray(params["variance"]["sigma"], dtype=float).reshape(d, d, G)

    return {
        "G": G,
        "modelName": model_name,
        "parameters": {"pro": par_pro, "mean": par_mean, "variance": par_variance},
        "nboot": nboot,
        "type": type,
        "nonfit": nonfit,
        "pro": pro_boot,
        "mean": mean_boot,
        "variance": var_boot,
    }


def print_MclustBootstrap(x: Any, digits: int | None = None, **_: Any) -> str:
    """Return the text printed by ``print.MclustBootstrap``."""
    _ = digits
    lines = ["'MclustBootstrap' object:", f"List of {len(x)}"]
    for key, value in x.items() if isinstance(x, Mapping) else []:
        if key == "parameters":
            lines.append("$ parameters:List of 3")
            continue
        a = np.asarray(value)
        if a.ndim == 0:
            kind = "num" if np.issubdtype(a.dtype, np.number) else "chr"
            val = str(value) if kind == "num" else f'"{value}"'
            lines.append(f"$ {key} : {kind} {val}")
        else:
            typ = "num" if np.issubdtype(a.dtype, np.floating) else "int"
            dims = ", ".join(f"1:{n}" if n != 1 else "1" for n in a.shape)
            values = " ".join(_r_number(v, 7) for v in a.reshape(-1, order="F"))
            lines.append(f"$ {key} : {typ} [{dims}] {values}".rstrip())
    return "\n".join(lines)


def _apply(a: np.ndarray, axis: int | tuple[int, ...], fn: Any) -> np.ndarray:
    return fn(a, axis=axis)


def summary_MclustBootstrap(
    object_: Any,
    what: str = "se",
    conf_level: float = 0.95,
    **_: Any,
) -> dict[str, Any]:
    """Compute standard errors, averages, or confidence intervals."""
    if what not in {"se", "ci", "ave"}:
        raise ValueError("what must be one of 'se', 'ci', or 'ave'")
    pro = np.asarray(_get(object_, "pro"), dtype=float)
    mean = np.asarray(_get(object_, "mean"), dtype=float)
    variance = np.asarray(_get(object_, "variance"), dtype=float)
    nboot, d, g = mean.shape
    typ = _get(object_, "type")
    nonfit = int(_get(object_, "nonfit", 0))
    if what == "se":
        out = {
            "pro": np.nanstd(pro, axis=0, ddof=1),
            "mean": np.nanstd(mean, axis=0, ddof=1),
            "variance": np.nanstd(variance, axis=0, ddof=1),
        }
        if typ == "jk":
            factor = np.sqrt((nboot - nonfit - 1) ** 2 / (nboot - nonfit))
            out = {k: v * factor for k, v in out.items()}
    elif what == "ave":
        out = {
            "pro": np.nanmean(pro, axis=0),
            "mean": np.nanmean(mean, axis=0),
            "variance": np.nanmean(variance, axis=0),
        }
    else:
        levels = ((1 - conf_level) / 2, (1 + conf_level) / 2)
        if typ == "jk":
            ave = {
                "pro": np.nanmean(pro, axis=0),
                "mean": np.nanmean(mean, axis=0),
                "variance": np.nanmean(variance[:, np.arange(d), np.arange(d), :], axis=0),
            }
            se = {
                "pro": np.nanstd(pro, axis=0, ddof=1),
                "mean": np.nanstd(mean, axis=0, ddof=1),
                "variance": np.nanstd(variance[:, np.arange(d), np.arange(d), :], axis=0, ddof=1),
            }
            factor = np.sqrt((nboot - nonfit - 1) ** 2 / (nboot - nonfit))
            zq = 1.959963984540054
            out = {k: np.stack((ave[k] - zq * factor * se[k], ave[k] + zq * factor * se[k])) for k in ave}
        else:
            out = {
                "pro": np.nanquantile(pro, levels, axis=0),
                "mean": np.nanquantile(mean, levels, axis=0),
                "variance": np.nanquantile(
                    variance[:, np.arange(d), np.arange(d), :], levels, axis=0
                ),
            }
    result = {
        "modelName": _get(object_, "modelName"),
        "G": int(_get(object_, "G", g)),
        "nboot": int(_get(object_, "nboot", nboot)),
        "type": typ,
        "d": d,
        "what": what,
        **({"conf.level": conf_level} if what == "ci" else {}),
        **out,
    }
    return result


def _r_number(x: float, digits: int = 7) -> str:
    return format(float(x), f".{digits}g")


def _r_vector(a: Any, digits: int = 7) -> str:
    arr = np.asarray(a).reshape(-1)
    return "[1] " + " ".join(_r_number(v, digits) for v in arr)


def print_summary_MclustBootstrap(
    x: Any, digits: int = 7, width: int = 80, **_: Any
) -> str:
    """Return the text printed by ``print.summary.MclustBootstrap``."""
    title = {"se": "standard errors", "ave": "averages", "ci": "confidence intervals"}[
        _get(x, "what")
    ]
    line = "-" * min(58, width)
    out = [
        line + " ",
        f"Resampling {title} ",
        line + " ",
        f"Model{' ' * 22}= {_get(x, 'modelName')} ",
        f"Num. of mixture components{' ' * 1}= {_get(x, 'G')} ",
        f"Replications{' ' * 15}= {_get(x, 'nboot')} ",
        f"Type{' ' * 23}= "
        + {
            "bs": "nonparametric bootstrap",
            "wlbs": "weighted likelihood bootstrap",
            "pb": "parametric bootstrap",
            "jk": "jackknife",
        }[_get(x, "type")] + " ",
    ]
    if _get(x, "what") == "ci":
        out.append(f"Confidence level{' ' * 11}= {_get(x, 'conf.level')}")
    out += ["", "Mixing probabilities:", _r_vector(_get(x, "pro"), digits), "", "Means:"]
    mean = np.asarray(_get(x, "mean"))
    if int(_get(x, "d")) == 1:
        out.append(_r_vector(mean, digits))
    else:
        out.append(str(mean))
    out += ["", "Variances:"]
    variance = np.asarray(_get(x, "variance"))
    out.append(_r_vector(variance, digits) if int(_get(x, "d")) == 1 else str(variance))
    return "\n".join(out)


def _floats(values: Any) -> list[float]:
    """Numeric vector as floats, with None mapped to NaN (R NA)."""
    return [math.nan if v is None else float(v) for v in np.atleast_1d(values)]


def _catwrap(text: str, width: int = 80) -> str:
    """R ``catwrap``: strwrap to ``width - 1`` columns, then cat with a trailing space."""
    wrapped = textwrap.wrap(text, width=width - 1) or [""]
    return "\n".join(wrapped) + " \n"


def _r_format_real(values: Any, digits: int = 7) -> list[str]:
    """R ``format()`` of a numeric vector (formatReal), padded to one common width."""
    nums = _floats(values)
    neg = 0
    mxl = rgt = mxsl = mxns = -(10**9)
    mnl = 10**9
    any_finite = False
    for v in nums:
        if math.isnan(v) or math.isinf(v):
            continue
        any_finite = True
        sgn = 1 if v < 0 else 0
        a = abs(v)
        if a == 0.0:
            kp, nsig, widens = 0, 1, False
        else:
            mantissa, exponent = f"{a:.{digits - 1}e}".split("e")
            kp = int(exponent)
            nsig = max(len(mantissa.replace(".", "").rstrip("0")), 1)
            widens = kp > 0 and a < 10.0**kp
        left = kp + 1 - (1 if widens else 0)
        sleft = sgn + (1 if left <= 0 else left)
        neg = max(neg, sgn)
        rgt = max(rgt, nsig - left)
        mxl = max(mxl, left)
        mnl = min(mnl, left)
        mxsl = max(mxsl, sleft)
        mxns = max(mxns, nsig)
    width = 0
    scientific, places = False, 0
    if any_finite:
        if mxl < 0:
            mxsl = 1 + neg
        if rgt < 0:
            rgt = 0
        wf = mxsl + rgt + (1 if rgt != 0 else 0)
        e = 2 if (mxl > 100 or mnl <= -99) else 1
        d = mxns - 1
        wsci = neg + (1 if d > 0 else 0) + d + 4 + e
        scientific = wf > wsci
        places = d if scientific else rgt
        width = wsci if scientific else wf
    cells = []
    for v in nums:
        if math.isnan(v):
            cells.append("NA")
        elif math.isinf(v):
            cells.append("Inf" if v > 0 else "-Inf")
        elif scientific:
            cells.append(f"{v:.{places}e}")
        else:
            cells.append(f"{v:.{places}f}")
    width = max([width] + [len(c) for c in cells])
    return [c.rjust(width) for c in cells]


def print_mclustBootstrapLRT(x: Any, width: int = 80, digits: int = 7, **_: Any) -> str:
    """Return the text printed by ``print.mclustBootstrapLRT``.

    Mirrors the R method: a banner, the model name and replication count,
    then a data frame with columns ``LRTS`` and ``bootstrap p-value`` whose
    rows are labelled ``g vs g+1``. Numeric columns use R's ``format`` at
    seven digits. The R column-wrapping rule for very wide output is not
    implemented; a two-column table never reaches it at the default width.
    """
    model = _get(x, "modelName")
    boot = _get(x, "boot")
    nrow = int(np.asarray(boot).shape[0]) if boot is not None else 0
    groups = [int(g) for g in np.atleast_1d(_get(x, "G"))]
    obs_cells = _r_format_real(_get(x, "obs"), digits)
    p_cells = _r_format_real(_get(x, "p.value", _get(x, "p_value")), digits)

    dash = "-" * min(61, width)
    out = [
        _catwrap(dash, width),
        _catwrap("Bootstrap sequential LRT for the number of mixture components", width),
        _catwrap(dash, width),
        f"{'Model':<12} = {model} \n",
        f"{'Replications':<12} = {nrow} \n",
    ]

    headers = ["LRTS", "bootstrap p-value"]
    columns = [obs_cells, p_cells]
    row_labels = [f"{g} vs {g + 1}".ljust(8) for g in groups]
    label_width = max([len(r) for r in row_labels] + [0])
    col_widths = [
        max([len(h)] + [len(c) for c in col])
        for h, col in zip(headers, columns)
    ]
    out.append(" " * label_width + "".join(
        " " + h.rjust(w) for h, w in zip(headers, col_widths)) + "\n")
    for i, label in enumerate(row_labels):
        out.append(label.ljust(label_width) + "".join(
            " " + col[i].rjust(w) for col, w in zip(columns, col_widths)) + "\n")
    return "".join(out)
