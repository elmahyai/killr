"""nnet, nnet.default, nnet.formula, and nnetHess."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

from nnet.design import model_parts
from nnet.engine import Net


class Fit(dict):
    """A fitted network. Fields use the same names as the R object."""

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def __setattr__(self, key, value):
        self[key] = value


def _colon(start, end):
    if start <= end:
        return list(range(start, end + 1))
    return list(range(start, end - 1, -1))


def _add_net(nconn, conn, nunits, sources, dests):
    conn = list(conn)
    nconn = list(nconn)
    for dest in dests:
        ns = nconn[dest + 1]
        added = list(sources)
        if nconn[dest] == ns:
            added = [0] + added
        built = []
        if ns > 1:
            built.extend(conn[:ns])
        built.extend(added)
        if len(conn) > ns:
            built.extend(conn[ns:])
        for unit in _colon(dest + 1, nunits):
            nconn[unit] += len(added)
        conn = built
    return nconn, conn


def _build_net(n_inputs, size, n_outputs, skip):
    counts = [int(n_inputs), int(size), int(n_outputs)]
    nunits = 1 + sum(counts)
    nconn = [0] * (nunits + 1)
    conn = []
    if counts[1] > 0:
        n0 = counts[0]
        n1 = n0 + counts[1]
        n2 = n1 + counts[2]
        nconn, conn = _add_net(nconn, conn, nunits, _colon(1, n0), _colon(n0 + 1, n1))
        nconn, conn = _add_net(nconn, conn, nunits, _colon(n0 + 1, n1), _colon(n1 + 1, n2))
    if skip:
        nconn, conn = _add_net(
            nconn,
            conn,
            nunits,
            _colon(1, counts[0]),
            _colon(1 + counts[0] + counts[1], nunits - 1),
        )
    return counts, nunits, nconn, conn


def _as_matrix(values):
    if isinstance(values, dict):
        columns = [np.asarray(column, dtype=np.float64).reshape(-1) for column in values.values()]
        return np.column_stack(columns)
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim != 2:
        raise ValueError("expected a numeric matrix")
    return np.array(array, dtype=np.float64, copy=True)


def _runif(count, low, high):
    try:
        from boot.rng import unif
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import unif
    width = high - low
    return [low + width * unif() for _ in range(count)]


def _indicators(labels, levels):
    rows = []
    for label in labels:
        rows.append([1.0 if label == level else 0.0 for level in levels])
    if not rows:
        return np.zeros((0, len(levels)), dtype=np.float64)
    return np.asarray(rows, dtype=np.float64)


def _warn_empty(levels):
    if len(levels) == 1:
        warnings.warn(f"group '{levels[0]}' is empty", stacklevel=3)
    else:
        quoted = " ".join(f"'{level}'" for level in levels)
        warnings.warn(f"groups {quoted} are empty", stacklevel=3)


def nnet_hess(net, x, y, weights=None):
    """Hessian of a fitted network at its weights."""
    x = _as_matrix(x)
    y = _as_matrix(y)
    if x.shape[0] != y.shape[0]:
        raise ValueError("dims of 'x' and 'y' must match")
    if weights is None:
        weights = np.ones(x.shape[0], dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if weights.shape[0] != x.shape[0] or np.any(weights < 0):
        raise ValueError("invalid weights vector")
    nw = len(net["wts"])
    decay = np.asarray(net["decay"], dtype=np.float64).reshape(-1)
    if decay.size == 1:
        decay = np.repeat(decay, nw)
    engine = Net()
    engine.set_net(
        net["n"],
        net["nconn"],
        net["conn"],
        decay,
        net["nsunits"],
        net["entropy"],
        net["softmax"],
        net["censored"],
    )
    return engine.hessian(x, y, weights, net["wts"])


def nnet_default(
    x,
    y,
    weights=None,
    size=None,
    Wts=None,
    mask=None,
    linout=False,
    entropy=False,
    softmax=False,
    censored=False,
    skip=False,
    rang=0.7,
    decay=0,
    maxit=100,
    Hess=False,
    trace=True,
    MaxNWts=1000,
    abstol=1.0e-4,
    reltol=1.0e-8,
    **_ignored,
):
    """Fit a single-hidden-layer network. The optimiser is the C routine."""
    if size is None:
        raise TypeError("argument 'size' is missing, with no default")
    x = _as_matrix(x)
    y = _as_matrix(y)
    if np.isnan(x).any():
        raise ValueError("missing values in 'x'")
    if np.isnan(y).any():
        raise ValueError("missing values in 'y'")
    if x.shape[0] != y.shape[0]:
        raise ValueError("nrows of 'x' and 'y' must match")
    linout = bool(linout)
    entropy = bool(entropy)
    softmax = bool(softmax)
    censored = bool(censored)
    if linout and entropy:
        raise ValueError("entropy fit only for logistic units")
    if softmax:
        linout = True
        entropy = False
    if censored:
        linout = True
        entropy = False
        softmax = True
    counts, nunits, nconn, conn = _build_net(x.shape[1], size, y.shape[1], bool(skip))
    if len(conn) == 0:
        raise ValueError("no weights to fit")
    if len(conn) > int(MaxNWts):
        raise ValueError(f"too many ({len(conn)}) weights")
    nsunits = nunits if not linout else nunits - counts[2]
    if softmax and y.shape[1] < 2:
        raise ValueError("'softmax = TRUE' requires at least two response categories")
    if Wts is None:
        if float(rang) > 0:
            wts = _runif(len(conn), -float(rang), float(rang))
        else:
            wts = [0.0] * len(conn)
    else:
        wts = [float(v) for v in np.asarray(Wts, dtype=np.float64).reshape(-1)]
    if len(wts) != len(conn):
        raise ValueError("weights vector of incorrect length")
    if mask is None:
        mask = [1] * len(wts)
    else:
        mask = [0 if int(v) == 0 else 1 for v in np.asarray(mask).reshape(-1)]
    if len(mask) != len(wts):
        raise ValueError("incorrect length of 'mask'")
    if trace:
        sys.stdout.write(f"# weights:  {len(wts)}")
        varying = sum(bit != 0 for bit in mask)
        if varying < len(wts):
            sys.stdout.write(f" ({varying} variable)\n")
        else:
            sys.stdout.write("\n")
        sys.stdout.flush()
    decay_arg = np.asarray(decay, dtype=np.float64).reshape(-1)
    if decay_arg.size == 1:
        decay_vec = [float(decay_arg[0])] * len(wts)
    else:
        decay_vec = [float(v) for v in decay_arg]
    if weights is None:
        weights = np.ones(x.shape[0], dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if weights.shape[0] != x.shape[0] or np.any(weights < 0):
        raise ValueError("invalid weights vector")
    engine = Net()
    engine.set_net(counts, nconn, conn, decay_vec, nsunits, entropy, softmax, censored)
    engine.prepare(x, y, weights)
    value, fail = engine.fit(wts, maxit, bool(trace), mask, abstol, reltol)
    fitted = engine.predict(x, wts)
    result = Fit()
    result["n"] = counts
    result["nunits"] = nunits
    result["nconn"] = nconn
    result["conn"] = conn
    result["nsunits"] = nsunits
    result["decay"] = decay_arg.copy()
    result["entropy"] = entropy
    result["softmax"] = softmax
    result["censored"] = censored
    result["value"] = float(value)
    result["wts"] = np.asarray(wts, dtype=np.float64)
    result["convergence"] = int(fail)
    result["fitted.values"] = fitted
    result["residuals"] = y - fitted
    if entropy:
        result["lev"] = ["0", "1"]
    if softmax:
        result["lev"] = [str(i + 1) for i in range(y.shape[1])]
    if Hess:
        result["Hessian"] = nnet_hess(result, x, y, weights)
    result["class"] = "nnet"
    return result


def _is_formula(value):
    return isinstance(value, str) and "~" in value


def nnet_formula(
    formula,
    data,
    weights=None,
    subset=None,
    na_action="na.omit",
    contrasts=None,
    **kwargs,
):
    """Fit a network from a formula. The intercept column is the bias."""
    parts = model_parts(formula, data, weights=weights, subset=subset, na_action=na_action)
    names = list(parts["names"])
    design = parts["x"]
    if "(Intercept)" in names:
        keep = [i for i, name in enumerate(names) if name != "(Intercept)"]
        design = design[:, keep] if keep else np.zeros((design.shape[0], 0))
        names = [names[i] for i in keep]
    if parts["y_kind"] == "factor":
        original = list(parts["levels"])
        labels = list(parts["y"])
        counts = [labels.count(level) for level in original]
        empty = [level for level, count in zip(original, counts) if count == 0]
        levels = original
        if empty:
            _warn_empty(empty)
            levels = [level for level, count in zip(original, counts) if count > 0]
            labels = list(labels)
        if len(original) == 2:
            index = {level: i for i, level in enumerate(levels)}
            response = np.array([index[label] for label in parts["y"]], dtype=np.float64).reshape(-1, 1)
            kwargs = dict(kwargs)
            kwargs.pop("entropy", None)
            kwargs.pop("softmax", None)
            result = nnet_default(design, response, parts["weights"], entropy=True, **kwargs)
            result["lev"] = original
        else:
            response = _indicators(parts["y"], levels)
            kwargs = dict(kwargs)
            kwargs.pop("entropy", None)
            kwargs.pop("softmax", None)
            result = nnet_default(design, response, parts["weights"], softmax=True, **kwargs)
            result["lev"] = original
    else:
        response = np.asarray(parts["y"], dtype=np.float64)
        if response.ndim == 1:
            response = response.reshape(-1, 1)
        result = nnet_default(design, response, parts["weights"], **kwargs)
    result["coefnames"] = names
    result["contrasts"] = contrasts
    result["class"] = ["nnet.formula", "nnet"]
    return result


def nnet(*args, **kwargs):
    """Dispatch on a formula or a numeric matrix, as nnet() does."""
    if args and _is_formula(args[0]):
        return nnet_formula(*args, **kwargs)
    if "formula" in kwargs and "x" not in kwargs:
        return nnet_formula(**kwargs)
    return nnet_default(*args, **kwargs)
