"""Hyperparameter search (e1071 ``tune`` only; not ``tune.svm`` or helpers)."""

from __future__ import annotations

import bisect
import statistics
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from e1071.tune import tune_control


def _boot_sample_int():
    try:
        from boot.rng import sample_int
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int
    return sample_int


def _expand_grid(ranges: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
    """Rows of R ``expand.grid(ranges)``: the first parameter varies fastest."""
    rows: list[dict[str, Any]] = [{}]
    for name, values in ranges.items():
        rows = [{**row, name: value} for value in list(values) for row in rows]
    return rows


def _cut_groups(n: int, n_breaks: int) -> list[list[int]]:
    """Folds of R ``tapply(1:n, cut(1:n, breaks = n_breaks), ...)``.

    R's ``cut`` uses right-closed intervals ``(b, b']`` and widens both ends
    by a thousandth of the range, so an integer on an interior break belongs
    to the lower fold.
    """
    dx = float(n - 1)
    step = dx / n_breaks
    breaks = [1.0 + i * step for i in range(n_breaks + 1)]
    breaks[0] = 1.0 - dx / 1000.0
    breaks[-1] = float(n) + dx / 1000.0
    groups: list[list[int]] = [[] for _ in range(n_breaks)]
    for i in range(1, n + 1):
        bin_idx = bisect.bisect_left(breaks, float(i)) - 1
        groups[bin_idx].append(i)
    return groups


def _r_negative_rows(n: int, remove: Sequence[int]) -> list[int]:
    remove_set = set(int(v) for v in remove)
    return [i for i in range(1, n + 1) if i not in remove_set]


def _is_factor_like(values: Sequence[Any]) -> bool:
    if values is None:
        return False
    return not all(isinstance(v, (bool, int, float)) for v in values)


def _unique_levels(values: Sequence[Any]) -> list[Any]:
    levels: list[Any] = []
    for value in values:
        if value not in levels:
            levels.append(value)
    return levels


def _cross_table(
    pred: Sequence[Any], true_y: Sequence[Any]
) -> tuple[list[Any], list[Any], list[list[int]]]:
    """Counts of ``table(pred, true.y)``: rows are prediction levels, columns truth levels."""
    pred = list(pred)
    true_y = list(true_y)
    row_levels = _unique_levels(pred)
    col_levels = _unique_levels(true_y)
    counts = [[0 for _ in col_levels] for _ in row_levels]
    for p, t in zip(pred, true_y, strict=True):
        counts[row_levels.index(p)][col_levels.index(t)] += 1
    return row_levels, col_levels, counts


def _inner_class_agreement(
    row_levels: Sequence[Any], col_levels: Sequence[Any], counts: Sequence[Sequence[int]]
) -> float:
    """R ``classAgreement``: the diagonal over the levels in both dimnames.

    ``lev <- intersect(colnames(tab), rownames(tab))``; ``sum(diag(tab[lev, lev])) / n``.
    Levels are matched by label, not by position.
    """
    n = sum(sum(row) for row in counts)
    shared = [level for level in col_levels if level in row_levels]
    diag = sum(counts[row_levels.index(level)][col_levels.index(level)] for level in shared)
    return diag / n


def _r_sd(values: Sequence[float]) -> float:
    seq = list(values)
    if len(seq) < 2:
        return float("nan")
    return float(statistics.stdev(seq))


def _resolve_method(method: str | Callable[..., Any]) -> tuple[Callable[..., Any], str]:
    if isinstance(method, str):
        if method == "svm":
            from e1071.svm import svm

            return svm, method
        raise ValueError(f"unknown METHOD {method!r}")
    name = getattr(method, "__name__", None) or str(method)
    return method, name


def _as_matrix_rows(x: Any) -> np.ndarray:
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    return np.asfortranarray(array)


def _control_fields(tunecontrol: Mapping[str, Any] | None) -> dict[str, Any]:
    base = tune_control() if tunecontrol is None else dict(tunecontrol)
    base.setdefault("repeat_aggregate", statistics.mean)
    base.setdefault("sampling_aggregate", statistics.mean)
    base.setdefault("sampling_dispersion", _r_sd)
    base.setdefault("error_fun", None)
    return base


def tune(
    method: str | Callable[..., Any],
    train_x: Any,
    train_y: Sequence[Any] | None = None,
    *,
    data: Mapping[str, Sequence[Any]] | None = None,
    validation_x: Any | None = None,
    validation_y: Sequence[Any] | None = None,
    ranges: Mapping[str, Sequence[Any]] | None = None,
    predict_func: Callable[..., Any] | None = None,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Search ``method`` over ``ranges`` with cross-validation or related sampling."""
    if predict_func is None:
        raise TypeError("predict_func is required")
    ctrl = _control_fields(tunecontrol)
    sample_int = _boot_sample_int()
    method_fn, method_name = _resolve_method(method)

    if ctrl["sampling"] == "cross":
        validation_x = None
        validation_y = None

    use_formula = train_y is None
    if use_formula:
        raise NotImplementedError("formula interface is not supported")

    if isinstance(train_y, Mapping):
        train_y = np.asarray(list(train_y.values())).T.tolist()

    if isinstance(train_x, np.ndarray) and train_x.ndim == 1:
        train_x = _as_matrix_rows(train_x)
    elif not isinstance(train_x, np.ndarray):
        train_x = np.asarray(train_x, dtype=float)
        if train_x.ndim == 1:
            train_x = train_x.reshape(1, -1)

    if validation_x is not None:
        ctrl = dict(ctrl)
        ctrl["fix"] = 1

    n = int(train_x.shape[0])
    perm_ind = sample_int(n, n, replace=False)

    if ctrl["sampling"] == "cross":
        if int(ctrl["cross"]) > n:
            raise ValueError("'cross' must not exceed sampling size!")
        if int(ctrl["cross"]) == 1:
            raise ValueError("'cross' must be greater than 1!")

    if ctrl["sampling"] == "cross":
        groups = _cut_groups(n, int(ctrl["cross"]))
        train_ind = []
        for fold in groups:
            # R ``perm.ind[-x]`` uses fold observation ids as positions into ``perm.ind``.
            remove_pos = list(fold)
            train_ind.append([perm_ind[i - 1] for i in range(1, n + 1) if i not in remove_pos])
    elif ctrl["sampling"] == "fix":
        k = int(n * ctrl["fix"])
        train_ind = [perm_ind[:k]]
    else:
        boot_n = int(n * ctrl["boot_size"])
        train_ind = [sample_int(n, boot_n, replace=True) for _ in range(int(ctrl["nboot"]))]

    if ranges is None:
        parameters = [{"dummyparameter": 0}]
    else:
        parameters = _expand_grid(ranges)

    p = len(parameters)
    random = ctrl["random"]
    if type(random) is int:
        if random < 1:
            raise ValueError("random must be a strictly positive integer")
        if random > p:
            random = p
        pick = sample_int(p, random, replace=False)
        parameters = [parameters[i - 1] for i in pick]
        p = len(parameters)

    model_errors: list[float] = []
    model_variances: list[float] = []

    for para_set in range(p):
        sampling_errors: list[float] = []
        for sample in range(len(train_ind)):
            repeat_errors: list[float] = []
            for _reps in range(int(ctrl["nrepeat"])):
                pars = None if ranges is None else {k: parameters[para_set][k] for k in parameters[para_set]}
                subset = train_ind[sample]
                if pars is None:
                    model = method_fn(train_x, y=train_y, subset=subset, **kwargs)
                else:
                    model = method_fn(train_x, y=train_y, subset=subset, **pars, **kwargs)

                if validation_x is not None:
                    pred_x = validation_x
                else:
                    hold_out = _r_negative_rows(n, train_ind[sample])
                    idx = [i - 1 for i in hold_out]
                    pred_x = train_x[idx, :]

                pred = predict_func(model, pred_x)

                if validation_y is not None:
                    true_y = validation_y
                else:
                    hold_out = _r_negative_rows(n, train_ind[sample])
                    idx = [i - 1 for i in hold_out]
                    true_y = [train_y[i] for i in idx]

                if true_y is None:
                    true_y = [True] * len(list(pred))

                pred_list = list(pred)
                true_list = list(true_y)

                error_fun = ctrl["error_fun"]
                if error_fun is not None:
                    err = float(error_fun(true_list, pred_list))
                elif (
                    all(isinstance(v, bool) for v in true_list)
                    or _is_factor_like(true_list)
                ) and (
                    all(isinstance(v, bool) for v in pred_list)
                    or _is_factor_like(pred_list)
                    or all(isinstance(v, str) for v in pred_list)
                ):
                    row_levels, col_levels, counts = _cross_table(pred_list, true_list)
                    err = 1.0 - _inner_class_agreement(row_levels, col_levels, counts)
                elif all(isinstance(v, (int, float)) for v in true_list) and all(
                    isinstance(v, (int, float)) for v in pred_list
                ):
                    diff = np.asarray(pred_list, dtype=float) - np.asarray(true_list, dtype=float)
                    err = float(diff @ diff) / len(pred_list)
                else:
                    raise ValueError("Dependent variable has wrong type!")
                repeat_errors.append(err)

            sampling_errors.append(float(ctrl["repeat_aggregate"](repeat_errors)))

        model_errors.append(float(ctrl["sampling_aggregate"](sampling_errors)))
        model_variances.append(float(ctrl["sampling_dispersion"](sampling_errors)))

    best = int(np.argmin(np.asarray(model_errors)))
    best_pars = None if ranges is None else {k: parameters[best][k] for k in parameters[best]}

    if ctrl["sampling"] == "fix":
        sampling_label = "fixed training/validation set"
    elif ctrl["sampling"] == "bootstrap":
        sampling_label = "bootstrapping"
    elif int(ctrl["cross"]) == n:
        sampling_label = "leave-one-out"
    else:
        sampling_label = f"{int(ctrl['cross'])}-fold cross validation"

    performances = None
    if ctrl["performances"]:
        performances = []
        for i, row in enumerate(parameters):
            perf_row = dict(row)
            perf_row["error"] = model_errors[i]
            perf_row["dispersion"] = model_variances[i]
            performances.append(perf_row)

    best_model = None
    if ctrl["best_model"]:
        if best_pars is None:
            best_model = method_fn(train_x, y=train_y, **kwargs)
        else:
            best_model = method_fn(train_x, y=train_y, **best_pars, **kwargs)

    return {
        "best.parameters": dict(parameters[best]),
        "best.performance": model_errors[best],
        "method": method_name,
        "nparcomb": len(parameters),
        "train.ind": train_ind,
        "sampling": sampling_label,
        "performances": performances,
        "best.model": best_model,
        "class": "tune",
    }
