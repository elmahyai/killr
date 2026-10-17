"""Support vector machine (e1071 ``svm``, ``svm.default`` only)."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from e1071.scale import scale_data_frame

_TYPE = (
    "C-classification",
    "nu-classification",
    "one-classification",
    "eps-regression",
    "nu-regression",
)
_KERNEL = ("linear", "polynomial", "radial", "sigmoid")


def _svm_ext():
    try:
        from svm import predict as svm_predict
        from svm import train as svm_train
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "svm"))
        from svm import predict as svm_predict
        from svm import train as svm_train
    return svm_train, svm_predict


def _pmatch(value: str | None, choices: Sequence[str]) -> int | None:
    if value is None:
        return None
    text = str(value)
    hits = [index for index, choice in enumerate(choices) if choice.startswith(text)]
    if not hits:
        return 99
    if len(hits) > 1:
        return 99
    return hits[0]


def _as_matrix(x: Any) -> np.ndarray:
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("Argument 'x' must be coercible to a matrix")
    return np.asfortranarray(array)


def _scale_columns(matrix: np.ndarray, scale_mask: np.ndarray) -> tuple[np.ndarray, dict[str, Any] | None]:
    if not np.any(scale_mask):
        return matrix, None
    subset = matrix[:, scale_mask]
    names = [f"V{i + 1}" for i in range(subset.shape[1])]
    frame = {name: list(subset[:, j]) for j, name in enumerate(names)}
    scaled = scale_data_frame(frame)
    out = matrix.copy()
    for j, name in enumerate(names):
        out[:, np.where(scale_mask)[0][j]] = scaled["columns"][name]
    x_scale = {
        "scaled:center": np.array([scaled["center"].get(name, 0.0) for name in names], dtype=float),
        "scaled:scale": np.array([scaled["scale"].get(name, 1.0) for name in names], dtype=float),
    }
    return out, x_scale


def _scale_newdata(model: dict[str, Any], newdata: np.ndarray) -> np.ndarray:
    scale_mask = np.asarray(model["scaled"], dtype=bool)
    if not np.any(scale_mask) or model.get("x.scale") is None:
        return np.asfortranarray(newdata, dtype=float)
    out = np.asfortranarray(newdata, dtype=float).copy()
    centers = model["x.scale"]["scaled:center"]
    scales = model["x.scale"]["scaled:scale"]
    cols = np.where(scale_mask)[0]
    for j, col in enumerate(cols):
        out[:, col] = (out[:, col] - centers[j]) / scales[j]
    return out


def _predict_svm(
    model: dict[str, Any],
    newdata: np.ndarray,
    *,
    decision_values: bool = False,
    probability: bool = False,
) -> tuple[np.ndarray, np.ndarray | None]:
    _, svm_predict = _svm_ext()
    newdata = _scale_newdata(model, newdata)
    sv = np.asarray(model["SV"], dtype=float)
    nr, nc = sv.shape
    flat_sv = np.ascontiguousarray(sv, dtype=float).reshape(-1, order="C")
    flat_x = np.ascontiguousarray(newdata, dtype=float).reshape(-1, order="C")
    coefs_vec = np.ascontiguousarray(model["coefs"], dtype=float).reshape(-1, order="F")
    rho = np.ascontiguousarray(model["rho"], dtype=float)
    labels = np.ascontiguousarray(model["labels"], dtype=np.int32)
    nsv = np.ascontiguousarray(model["nSV"], dtype=np.int32)
    prob_a = model.get("probA")
    prob_b = model.get("probB")
    result = svm_predict(
        flat_sv,
        coefs_vec,
        rho,
        flat_x,
        tot_nsv=nr,
        sv_nc=nc,
        svm_type=int(model["type"]),
        kernel_type=int(model["kernel"]),
        degree=int(model["degree"]),
        gamma=float(model["gamma"]),
        coef0=float(model["coef0"]),
        nclasses=int(model["nclasses"]),
        labels=labels,
        nsv=nsv,
        compprob=bool(model.get("compprob")),
        prob_a=None if prob_a is None else np.ascontiguousarray(prob_a, dtype=float),
        prob_b=None if prob_b is None else np.ascontiguousarray(prob_b, dtype=float),
        sparse_model=bool(model.get("sparse")),
        decision_values=decision_values,
        probability=probability,
    )
    values = np.asarray(result["values"], dtype=float)
    dec = None
    if decision_values:
        dec = np.asarray(result["decision_values"], dtype=float)
    return values, dec


def svm(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    scale: bool | Sequence[bool] = True,
    type: str | None = None,
    kernel: str = "radial",
    degree: int = 3,
    gamma: float | None = None,
    coef0: float = 0.0,
    cost: float = 1.0,
    nu: float = 0.5,
    class_weights: Mapping[str, float] | str | None = None,
    cachesize: float = 40.0,
    tolerance: float = 0.001,
    epsilon: float = 0.1,
    shrinking: bool = True,
    cross: int = 0,
    probability: bool = False,
    fitted: bool = True,
    subset: Sequence[int] | None = None,
):
    """Fit an SVM; matrix interface matching ``svm.default`` (not formula or ``predict.svm``)."""
    if degree is None:
        raise ValueError("'degree' must not be NULL!")
    if gamma is None:
        gamma = 1.0 if np.asarray(x).ndim == 1 else 1.0 / _as_matrix(x).shape[1]
    for name, value in (
        ("gamma", gamma),
        ("coef0", coef0),
        ("cost", cost),
        ("nu", nu),
        ("epsilon", epsilon),
        ("tolerance", tolerance),
    ):
        if value is None:
            raise ValueError(f"'{name}' must not be NULL!")

    x = _as_matrix(x)
    yorig = None if y is None else list(y)
    xhold = x.copy() if fitted else None

    type_code = _pmatch(
        type,
        _TYPE,
    ) if type is not None else (
        2 if y is None else (0 if _is_factor_like(y) else 3)
    )
    if type_code == 99:
        raise ValueError("wrong type specification!")
    kernel_code = _pmatch(kernel, _KERNEL)
    if kernel_code == 99:
        raise ValueError("wrong kernel specification!")

    if subset is not None:
        idx = np.asarray(subset, dtype=int) - 1
        x = x[idx, :]
        if yorig is not None:
            yorig = [yorig[i] for i in idx]
        if xhold is not None:
            xhold = xhold[idx, :]

    scale_mask = np.asarray(scale, dtype=bool)
    if scale_mask.ndim == 0 or scale_mask.size == 1:
        scale_mask = np.full(x.shape[1], bool(scale_mask))
    elif scale_mask.size != x.shape[1]:
        scale_mask = np.resize(scale_mask, x.shape[1])

    y_scale = None
    x_scale = None
    if np.any(scale_mask):
        variances = np.var(x[:, scale_mask], axis=0, ddof=1)
        if np.any(variances == 0):
            warnings.warn(
                "Variable(s) constant. Cannot scale data.",
                RuntimeWarning,
                stacklevel=2,
            )
            scale_mask = np.zeros(x.shape[1], dtype=bool)
        else:
            x, x_scale = _scale_columns(x, scale_mask)
            if yorig is not None and type_code > 2 and all(
                isinstance(v, (int, float)) for v in yorig
            ):
                y_arr = np.asarray(yorig, dtype=float)
                y_scaled = scale_data_frame({"y": list(y_arr)})
                y_scale = {
                    "scaled:center": y_scaled["center"]["y"],
                    "scaled:scale": y_scaled["scale"]["y"],
                }
                yorig = list(y_arr)
    y = yorig

    nr = x.shape[0]
    if cross > nr:
        raise ValueError("'cross' cannot exceed the number of observations!")

    if cachesize < 0.1:
        cachesize = 0.1

    lev: list[Any] | None = None
    weightlabels: np.ndarray | None = None
    weights: np.ndarray | None = None

    if type_code == 2:
        y_train = np.ones(nr, dtype=float)
    elif y is None:
        raise ValueError("y must be supplied except for one-classification")
    else:
        if type_code != 2 and len(y) != nr:
            raise ValueError("x and y don't match.")
        if _is_factor_like(y):
            lev, y_int = _factor_to_int(y)
            y_train = np.asarray(y_int, dtype=float)
        elif type_code < 3:
            if any(int(v) != float(v) for v in y):
                raise ValueError(
                    "dependent variable has to be of factor or integer type for classification mode."
                )
            lev, y_int = _factor_to_int(y)
            y_train = np.asarray(y_int, dtype=float)
        else:
            if not all(isinstance(v, (int, float)) for v in y):
                raise ValueError("Need numeric dependent variable for regression.")
            lev = sorted({float(v) for v in y})
            y_train = np.asarray(y, dtype=float)

    if type_code < 3 and class_weights is not None:
        if isinstance(class_weights, str) and class_weights == "inverse":
            counts = np.bincount(y_train.astype(int))
            class_weights = {lev[i]: 1.0 / counts[i + 1] for i in range(len(lev))}
        if not isinstance(class_weights, Mapping):
            raise ValueError("Weights have to be specified along with their according level names !")
        weightlabels = []
        weights = []
        for level_name, weight in class_weights.items():
            if level_name not in lev:
                raise ValueError("At least one level name is missing or misspelled.")
            weightlabels.append(lev.index(level_name) + 1)
            weights.append(float(weight))
        weightlabels = np.asarray(weightlabels, dtype=np.int32)
        weights = np.asarray(weights, dtype=float)
    elif type_code > 1 and class_weights:
        warnings.warn(
            "'class.weights' are set to NULL for regression mode.",
            RuntimeWarning,
            stacklevel=2,
        )

    flat_x = np.ascontiguousarray(x, dtype=float).reshape(-1, order="C")
    svm_train, _ = _svm_ext()
    trained = svm_train(
        flat_x,
        y_train,
        svm_type=type_code,
        kernel_type=kernel_code,
        degree=int(degree),
        gamma=float(gamma),
        coef0=float(coef0),
        cost=float(cost),
        nu=float(nu),
        weight_labels=weightlabels,
        weights=weights,
        cachesize=float(cachesize),
        tolerance=float(tolerance),
        epsilon=float(epsilon),
        shrinking=bool(shrinking),
        cross=int(cross),
        sparse=False,
        probability=bool(probability),
    )

    index = np.asarray(trained["index"], dtype=int)
    tot_nsv = int(trained["tot_nsv"])
    nclasses = int(trained["nclasses"])
    labels = np.asarray(trained["labels"], dtype=int)
    nsv = np.asarray(trained["nSV"], dtype=int)
    rho = np.asarray(trained["rho"], dtype=float)
    coefs_raw = np.asarray(trained["coefs"], dtype=float)
    if tot_nsv == 0:
        coefs = None
    else:
        coefs = coefs_raw.reshape((nclasses - 1, tot_nsv), order="C").T

    sv = x[index - 1, :]

    ret: dict[str, Any] = {
        "type": type_code,
        "kernel": kernel_code,
        "cost": cost,
        "degree": degree,
        "gamma": gamma,
        "coef0": coef0,
        "nu": nu,
        "epsilon": epsilon,
        "sparse": False,
        "scaled": scale_mask,
        "x.scale": x_scale,
        "y.scale": y_scale,
        "nclasses": nclasses,
        "levels": lev,
        "tot.nSV": tot_nsv,
        "nSV": nsv,
        "labels": labels,
        "SV": sv,
        "index": index,
        "rho": rho,
        "compprob": probability,
        "probA": None if not probability else np.asarray(trained.get("probA"), dtype=float),
        "probB": None if not probability else np.asarray(trained.get("probB"), dtype=float),
        "sigma": None if not probability else float(trained.get("sigma", 0.0)),
        "coefs": coefs,
    }

    if cross > 0:
        cresults = np.asarray(trained["cresults"], dtype=float)
        if type_code > 2:
            scale_factor = (
                float(y_scale["scaled:scale"]) ** 2 if y_scale is not None else 1.0
            )
            ret["MSE"] = cresults * scale_factor
            ret["tot.MSE"] = float(trained["ctotal1"]) * scale_factor
            ret["scorrcoeff"] = float(trained["ctotal2"])
        else:
            ret["accuracies"] = cresults
            ret["tot.accuracy"] = float(trained["ctotal1"])

    if fitted and xhold is not None:
        pred_vals, dec = _predict_svm(ret, xhold, decision_values=True)
        if lev is not None and type_code < 3 and not (type_code == 2):
            fitted_out = np.array([lev[int(v) - 1] for v in pred_vals], dtype=object)
        elif type_code == 2:
            fitted_out = pred_vals == 1.0
        elif y_scale is not None:
            fitted_out = pred_vals * y_scale["scaled:scale"] + y_scale["scaled:center"]
        else:
            fitted_out = pred_vals
        ret["fitted"] = fitted_out
        if dec is not None and lev is not None and type_code < 3:
            ncol = nclasses * (nclasses - 1) // 2
            dec_matrix = dec.reshape(-1, ncol)
            ret["decision.values"] = dec_matrix
        if type_code > 1 and yorig is not None:
            y_orig_arr = np.asarray(yorig, dtype=float)
            ret["residuals"] = y_orig_arr - np.asarray(fitted_out, dtype=float)

    return ret


def _is_factor_like(y: Sequence[Any]) -> bool:
    return not all(isinstance(v, (int, float)) for v in y)


def _factor_to_int(y: Sequence[Any]) -> tuple[list[Any], list[int]]:
    if all(isinstance(v, bool) for v in y):
        levels = [False, True]
    else:
        levels = sorted({v for v in y}, key=lambda item: str(item))
    mapping = {level: index + 1 for index, level in enumerate(levels)}
    return levels, [mapping[v] for v in y]
