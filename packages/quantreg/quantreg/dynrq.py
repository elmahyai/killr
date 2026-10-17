"""Dynamic linear quantile regression: dynrq and its print and summary methods.

A series is a regular ts: its values, the time of the first value, and the
frequency. The model frame follows R's dynformula. L(), d(), trend(), and
season() are evaluated on the grid of the response. The terms are merged on
the index with all = FALSE, rows with NA are dropped, and start and end pick
the rows. The point estimate is the Barrodale-Roberts linear program
(method "br") through rq_fit. Other methods run the Fortran path, which this
module does not translate.

zoo is not called. The index follows zoo's calendar: yearmon for frequency 12,
yearqtr for frequency 4, and the time otherwise.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import reduce

import numpy as np

from quantreg.anova import summary_rqs
from quantreg.fit import rq_fit
from quantreg.model import _rho

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
TS_EPS = 1e-5
_CALL = re.compile(r"^([A-Za-z.][A-Za-z0-9._]*)\((.*)\)$", re.S)
_NAME = re.compile(r"^[A-Za-z.][A-Za-z0-9._]*$")


@dataclass(frozen=True)
class Ts:
    """A regular series: values, the time of the first value, and the frequency."""

    values: np.ndarray
    start: float
    frequency: float


def ts_series(values, start=1.0, frequency=1.0):
    """R's ts(values, start, frequency). start is (year, cycle) or a time."""
    f = float(frequency)
    if isinstance(start, (tuple, list)):
        t0 = float(start[0]) + (float(start[1]) - 1.0) / f
    else:
        t0 = float(start)
    return Ts(np.asarray(values, dtype=float).reshape(-1), t0, f)


def _split_top(text, sep):
    """Split at sep outside parentheses."""
    parts, depth, current = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return parts


def _normalize_arg(text):
    text = text.strip()
    if text.startswith("c(") and text.endswith(")"):
        items = [item.strip() for item in text[2:-1].split(",")]
        return "c(" + ", ".join(items) + ")"
    return text


def _integers(text):
    """R's integer vector written as a scalar, c(...), or a:b."""
    text = text.replace(" ", "")
    if text.startswith("c(") and text.endswith(")"):
        return [int(float(item)) for item in text[2:-1].split(",") if item]
    if ":" in text:
        first, last = text.split(":", 1)
        a, b = int(float(first)), int(float(last))
        step = 1 if b >= a else -1
        return list(range(a, b + step, step))
    return [int(float(text))]


def _window_time(value, frequency):
    """start = c(year, cycle) becomes year + (cycle - 1) / frequency, as in R."""
    if isinstance(value, (tuple, list)):
        return float(value[0]) + (float(value[1]) - 1.0) / frequency
    return float(value)


@dataclass(frozen=True)
class _Term:
    pos: np.ndarray  # sorted grid positions where the term is defined
    columns: np.ndarray  # one row per position, one column per model column
    names: tuple


def _evaluate(expression, data, base):
    """One formula term on the grid of the response series base."""
    text = expression.strip()
    match = _CALL.match(text)
    if match is None:
        if not _NAME.match(text):
            raise NotImplementedError(f"term {text!r} is not a variable or a call to L, d, trend, or season")
        series = _lookup(text, data, base)
        n = series.values.size
        return _Term(np.arange(n), series.values.reshape(-1, 1), (text,))

    fname = match.group(1)
    args = [_normalize_arg(item) for item in _split_top(match.group(2), ",")]
    label = f"{fname}({', '.join(args)})"
    if not _NAME.match(args[0]):
        raise NotImplementedError(f"nested call {args[0]!r} inside {fname}() is not translated")
    series = _lookup(args[0], data, base)
    n = series.values.size
    f = series.frequency
    values = series.values

    if fname == "L":
        lags = _integers(args[1]) if len(args) > 1 else [1]
        source = np.arange(n)
        pieces = []
        for lag in lags:
            target = source + lag
            keep = (target >= 0) & (target < n)
            pieces.append((target[keep], values[source[keep]]))
        common = reduce(np.intersect1d, [target for target, _ in pieces])
        columns = [vals[np.searchsorted(target, common)] for target, vals in pieces]
        names = (label,) if len(lags) == 1 else tuple(f"{label}{lag}" for lag in lags)
        return _Term(common, np.column_stack(columns), names)

    if fname == "d":
        lag = _integers(args[1])[0] if len(args) > 1 else 1
        if lag <= 0:
            raise ValueError("d() needs a positive lag")
        pos = np.arange(lag, n)
        return _Term(pos, (values[lag:] - values[:-lag]).reshape(-1, 1), (label,))

    if fname == "trend":
        scaled = not (len(args) > 1 and args[1].replace(" ", "") == "scale=FALSE")
        freq = round(f) if scaled else 1
        return _Term(np.arange(n), ((np.arange(n) + 1.0) / freq).reshape(-1, 1), (label,))

    if fname == "season":
        if len(args) > 1:
            raise NotImplementedError("season(ref=) is not in the checked path")
        freq = int(round(f))
        if freq == 12:
            levels = MONTHS
        elif freq == 4:
            levels = ("Q1", "Q2", "Q3", "Q4")
        else:
            levels = tuple(str(i) for i in range(1, freq + 1))
        first_cycle = int(round((series.start - math.floor(series.start + TS_EPS)) * freq))
        cycle = (first_cycle + np.arange(n)) % freq
        columns = np.column_stack([(cycle == j).astype(float) for j in range(1, freq)])
        names = tuple(f"{label}{levels[j]}" for j in range(1, freq))
        return _Term(np.arange(n), columns, names)

    if fname == "harmon":
        raise NotImplementedError("harmon() is not in the checked path")
    raise NotImplementedError(f"{fname}() is not translated in dynrq")


def _lookup(name, data, base):
    if name not in data:
        raise KeyError(f"object '{name}' not found")
    series = data[name]
    if series.start != base.start or series.frequency != base.frequency:
        raise ValueError("the series must share the start and frequency of the response")
    return series


def _index_values(times, frequency):
    """zoo's index of a ts: yearmon, yearqtr, or the time."""
    if frequency == 12:
        return np.floor(12.0 * times + 0.0001) / 12.0
    if frequency == 4:
        return np.floor(4.0 * times + 0.001) / 4.0
    return times


def _model_frame(formula, data, start, end):
    """model.frame.dynformula plus the start and end rows of dynrq."""
    if formula.count("~") != 1:
        raise ValueError("formula needs exactly one ~")
    lhs, rhs = (part.strip() for part in formula.split("~"))
    first = _CALL.match(lhs)
    base_name = first.group(2).split(",")[0].strip() if first else lhs
    if not _NAME.match(base_name):
        raise NotImplementedError("the response must be a series name or a call on one")
    base = data[base_name]
    response = _evaluate(lhs, data, base)

    if len(_split_top(rhs, "-")) > 1 or "0" in _split_top(rhs, "+"):
        raise NotImplementedError("formulas without an intercept are not in the checked path")
    parts = [part for part in _split_top(rhs, "+") if part != "1"]
    terms = [_evaluate(part, data, base) for part in parts]

    pos = reduce(np.intersect1d, [response.pos, *[term.pos for term in terms]])
    columns = [np.ones(pos.size)]
    names = ["(Intercept)"]
    for term in terms:
        block = term.columns[np.searchsorted(term.pos, pos)]
        columns.extend(block[:, j] for j in range(block.shape[1]))
        names.extend(term.names)
    y = response.columns[np.searchsorted(response.pos, pos), 0]
    design = np.column_stack(columns)

    keep = np.all(np.isfinite(np.column_stack([y, design])), axis=1)
    pos, y, design = pos[keep], y[keep], design[keep]

    f = base.frequency
    times = base.start + pos / f
    index = _index_values(times, f)
    lo, hi = 0, pos.size - 1
    if start is not None:
        hits = np.nonzero(index >= _window_time(start, f))[0]
        if hits.size == 0:
            raise ValueError("start is after the last observation")
        lo = int(hits[0])
    if end is not None:
        hits = np.nonzero(index <= _window_time(end, f))[0]
        if hits.size == 0:
            raise ValueError("end is before the first observation")
        hi = int(hits[-1])
    if hi < lo:
        raise ValueError("empty model frame specified")
    window = slice(lo, hi + 1)
    return {
        "pos": pos[window],
        "times": times[window],
        "index": index[window],
        "y": y[window],
        "X": design[window],
        "names": names,
        "frequency": f,
    }


def dynrq(formula, data, tau=0.5, method="br", start=None, end=None):
    """Dynamic linear quantile regression on a formula with L(), d(), trend(), season().

    data maps each series name to a Ts from ts_series. A vector tau gives a
    dynrqs fit with one column per tau in the order given. Only method "br"
    is translated here. Other methods run the Fortran path.
    """
    if method != "br":
        raise NotImplementedError(
            f"method {method!r} runs the Fortran rq.fit path, which is not translated in this module"
        )
    frame = _model_frame(formula, data, start, end)
    design, y = frame["X"], frame["y"]
    n, p = design.shape
    taus = np.atleast_1d(np.asarray(tau, dtype=float))
    if taus.size == 1:
        fit = rq_fit(design, y, tau=float(taus[0]), method="br")
        coefficients = np.asarray(fit["coefficients"], dtype=float)
        residuals = y - design @ coefficients
        rho = _rho(residuals, float(taus[0]))
        dual = fit["dual"]
        tau_out = float(taus[0])
        klass = "dynrq"
    else:
        coefficients = np.empty((p, taus.size))
        residuals = np.empty((n, taus.size))
        rho = np.empty(taus.size)
        dual = None
        for i, value in enumerate(taus):
            fit = rq_fit(design, y, tau=float(value), method="br")
            coefficients[:, i] = fit["coefficients"]
            residuals[:, i] = y - design @ coefficients[:, i]
            rho[i] = _rho(residuals[:, i], float(value))
            dual = fit["dual"]
        tau_out = taus
        klass = "dynrqs"
    fitted = y - residuals if residuals.ndim == 1 else y.reshape(-1, 1) - residuals
    times = frame["times"]
    return {
        "coefficients": coefficients,
        "residuals": residuals,
        "fitted.values": fitted,
        "rho": rho,
        "tau": tau_out,
        "dual": dual,
        "x": design,
        "X": design,
        "y": y,
        "names": frame["names"],
        "index": frame["index"],
        "frequency": frame["frequency"],
        "tsp": (float(times[0]), float(times[-1]), frame["frequency"]),
        "method": "br",
        "formula": formula,
        "call": f"dynrq(formula = {formula}, tau = {tau})",
        "class": klass,
    }


def _tsp_start(time, frequency):
    """start.default: the year and the cycle of a time on the grid."""
    year = math.floor(time + TS_EPS)
    cycle = round((time - year) * frequency) + 1
    return float(year), float(cycle)


def index_dynrq(x):
    """index.dynrq: the zoo index of the rows used in the fit."""
    return np.asarray(x["index"], dtype=float)


def start_dynrq(x):
    """start.dynrq: start of the residuals. A matrix of residuals has no tsp, so R gives (1, 1)."""
    if x["class"] != "dynrq":
        return np.array([1.0, 1.0])
    time, _last, frequency = x["tsp"]
    return np.array(_tsp_start(time, frequency))


def end_dynrq(x):
    """end.dynrq: end of the residuals. A matrix of residuals gives (number of rows, 1)."""
    if x["class"] != "dynrq":
        return np.array([float(np.asarray(x["residuals"]).shape[0]), 1.0])
    _first, last, frequency = x["tsp"]
    return np.array(_tsp_start(last, frequency))


def _header(x):
    """The Start and End pair printed by print.dynrq and print.dynrqs."""
    first, last, frequency = x["tsp"]
    return np.array([*_tsp_start(first, frequency), *_tsp_start(last, frequency)])


def print_dynrq(x):
    """print.dynrq: the Start and End pair, the coefficients, and the observation count and residual df."""
    coefficient = np.asarray(x["coefficients"], dtype=float)
    nobs = np.asarray(x["residuals"]).shape[0]
    rdf = nobs - coefficient.shape[0]
    return np.concatenate([_header(x), coefficient.ravel(order="F"), [nobs, rdf]])


def print_dynrqs(x):
    """print.dynrqs: the same numbers as print.dynrq, with the coefficient matrix."""
    return print_dynrq(x)


def summary_dynrqs(object, se="nid", covariance=False, hs=True):
    """summary.dynrqs: summary.rq at each tau. The first summary is marked summary.dynrq."""
    pieces = summary_rqs(object, se=se, covariance=covariance, hs=hs)
    if pieces:
        pieces[0]["class"] = "summary.dynrq"
        pieces[0]["n"] = int(np.asarray(object["residuals"]).shape[0])
    return pieces


def print_summary_dynrq(x):
    """print.summary.dynrq: the header counts the residual positions, then the table.

    R prints Start = 1 and End = n here, because the summary residuals carry no zoo index.
    """
    table = np.asarray(x["coefficients"], dtype=float)
    return np.concatenate([[1.0, float(x["n"])], table.ravel(order="F")])


def print_summary_dynrqs(x):
    """print.summary.dynrqs: the first summary with its header, then the other tables."""
    if not x:
        return np.array([])
    tables = [np.asarray(piece["coefficients"], dtype=float).ravel(order="F") for piece in x[1:]]
    return np.concatenate([print_summary_dynrq(x[0]), *tables])
