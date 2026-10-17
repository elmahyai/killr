"""Matplotlib translation of R's ``plot.MclustDA`` method."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .coord_proj import coordProj
from .mclust_1d_plot import mclust1Dplot
from .plot_log import PlotLog
from .predict_mclust_da import predict_mclust_da

__all__ = ["plot_MclustDA"]


def _get(x: Any, name: str) -> Any:
    return x[name] if isinstance(x, dict) else getattr(x, name)


def _levels(values: Sequence[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value)
        if text not in out:
            out.append(text)
    return out


def _class_indices(values: Sequence[Any], levels: list[str]) -> np.ndarray:
    return np.asarray([levels.index(str(v)) for v in values], dtype=int)


def plot_MclustDA(
    x: Any,
    what: Sequence[str] | str = ("scatterplot", "classification", "train&test", "error"),
    newdata: Any = None,
    newclass: Sequence[Any] | None = None,
    dimens: Sequence[int] | None = None,
    symbols: Sequence[Any] | None = None,
    colors: Sequence[str] | None = None,
    main: Any = None,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> PlotLog:
    """Draw MclustDA scatter, classification, train/test, or error panels.

    The returned :class:`PlotLog` contains the numeric drawing data.  ``newdata``
    is intentionally optional, matching R's training-data default.
    """
    del main
    if log is None:
        log = PlotLog()
    choices = [what] if isinstance(what, str) else list(what)
    allowed = ("scatterplot", "classification", "train&test", "error")
    bad = [item for item in choices if item not in allowed]
    if bad:
        raise ValueError("'what' should be one of " + ", ".join(repr(v) for v in allowed))

    data = np.asarray(_get(x, "data"), dtype=float)
    if data.ndim == 1:
        data = data[:, None]
    n, p = data.shape
    dims = list(range(p)) if dimens is None else [int(i) - 1 for i in dimens if 1 <= int(i) <= p]
    if not dims:
        return log
    test = None if newdata is None else np.asarray(newdata, dtype=float)
    if test is not None and test.ndim == 1:
        test = test[:, None]
    if test is not None and test.shape[1] != p:
        raise ValueError("incompatible newdata dimensionality")
    if test is not None and newclass is not None and len(newclass) != len(test):
        raise ValueError("incompatible newdata and newclass")

    train_class = list(_get(x, "class"))
    train_levels = _levels(train_class)
    pred_train = np.asarray(predict_mclust_da(x, data)["classification"], dtype=object)
    pred_test = (
        np.asarray(predict_mclust_da(x, test)["classification"], dtype=object)
        if test is not None else None
    )
    cls_levels = _levels(train_class)
    cols = list(colors) if colors is not None else [
        "dodgerblue2", "red3", "green3", "slateblue", "darkorange", "skyblue1"
    ]
    syms = list(symbols) if symbols is not None else [16, 17, 15, 3, 7, 8]
    if len(cols) == 1:
        cols *= max(1, len(cls_levels))
    if len(syms) == 1:
        syms *= max(1, len(cls_levels))
    if len(cols) < len(cls_levels):
        cols = ["black"] * len(cls_levels)
    if len(syms) < len(cls_levels):
        syms = [16] * len(cls_levels)

    def draw_points(values: np.ndarray, classes: Sequence[Any], target: Any) -> None:
        labels = _class_indices(classes, cls_levels)
        if values.shape[1] == 1:
            mclust1Dplot(values[:, :1], classification=np.asarray(classes, dtype=object),
                         what="classification", ax=target, log=log)
        elif values.shape[1] == 2:
            log.window(target, (float(values[:, 0].min()), float(values[:, 0].max())),
                       (float(values[:, 1].min()), float(values[:, 1].max())))
            for k in range(len(cls_levels)):
                mask = labels == k
                if mask.any():
                    log.points(target, values[mask, 0], values[mask, 1], syms[k], cols[k])
        else:
            for i in range(values.shape[1]):
                for j in range(values.shape[1]):
                    if i != j:
                        target_i = None
                        coordProj(values, dimens=(j + 1, i + 1), classification=classes,
                                  symbols=syms, colors=cols, ax=target_i, log=log)

    for mode in choices:
        if mode == "scatterplot":
            shown = data if test is None else test
            known = train_class if test is None else (newclass if newclass is not None else pred_test)
            draw_points(shown[:, dims], known, ax)
        elif mode == "classification":
            shown = data if test is None else test
            predicted = pred_train if test is None else pred_test
            draw_points(shown[:, dims], predicted, ax)
        elif mode == "train&test":
            if test is None:
                raise ValueError("newdata is required for 'train&test'")
            both = np.vstack((data, test))[:, dims]
            if both.shape[1] == 1:
                # The one-dimensional R branch uses the same class plot helper;
                # concatenate the two sets and use distinct plotting symbols.
                mclust1Dplot(both, classification=np.array([1] * n + [2] * len(test)),
                             what="classification", ax=ax, log=log)
            else:
                log.window(ax, (float(both[:, 0].min()), float(both[:, 0].max())),
                           (float(both[:, 1].min()), float(both[:, 1].max())))
                log.points(ax, data[:, dims[0]], data[:, dims[1]], 1, "black")
                log.points(ax, test[:, dims[0]], test[:, dims[1]], 16, "black")
        elif mode == "error":
            shown = data if test is None else test
            predicted = pred_train if test is None else pred_test
            truth = train_class if test is None else newclass
            if truth is None:
                raise ValueError("newclass is required for test error plots")
            wrong = np.asarray([str(a) != str(b) for a, b in zip(predicted, truth)])
            draw_points(shown[:, dims], truth, ax)
            if shown.shape[1] >= 2 and wrong.any():
                log.points(ax, shown[wrong, 0], shown[wrong, 1], 16, "black")
    return log
