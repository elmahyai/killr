"""Write a fitted SVM in libsvm text format (e1071 ``write.svm``)."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


def _svmwrite_ext():
    try:
        from svmwrite import write_model as svmwrite_model
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "svmwrite"))
        from svmwrite import write_model as svmwrite_model
    return svmwrite_model


def _r_character_double(value: float) -> str:
    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    fixed = fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
    if fixed == "":
        fixed = "0"
    text = f"-{fixed}" if negative else fixed
    return sci if len(sci) < len(text) else text


def _write_scale_table(path: str, center: Sequence[float], scale: Sequence[float]) -> None:
    centers = np.asarray(center, dtype=float).reshape(-1)
    scales = np.asarray(scale, dtype=float).reshape(-1)
    lines = [
        f"{_r_character_double(float(c))} {_r_character_double(float(s))}"
        for c, s in zip(centers, scales, strict=True)
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _support_vector_arrays(
    object: Mapping[str, Any],
) -> tuple[np.ndarray, int, int, np.ndarray | None, np.ndarray | None, bool]:
    sparse = bool(object.get("sparse", False))
    sv = object["SV"]
    if sparse:
        if hasattr(sv, "ra"):
            ra = sv.ra
            ia = sv.ia
            ja = sv.ja
            nrow = int(sv.nrow)
            ncol = int(sv.ncol)
        elif isinstance(sv, Mapping):
            ra = sv["ra"]
            ia = sv["ia"]
            ja = sv["ja"]
            dim = sv["dimension"]
            nrow = int(dim[0])
            ncol = int(dim[1])
        else:
            ra = getattr(sv, "ra")
            ia = getattr(sv, "ia")
            ja = getattr(sv, "ja")
            dim = getattr(sv, "dimension")
            nrow = int(dim[0])
            ncol = int(dim[1])
        v = np.ascontiguousarray(ra, dtype=float)
        rowindex = np.ascontiguousarray(ia, dtype=np.int32)
        colindex = np.ascontiguousarray(ja, dtype=np.int32)
        return v, nrow, ncol, rowindex, colindex, True

    sv_arr = np.asarray(sv, dtype=float)
    if sv_arr.ndim != 2:
        raise ValueError("SV must be a matrix")
    nrow, ncol = sv_arr.shape
    v = np.ascontiguousarray(sv_arr, dtype=float).reshape(-1, order="C")
    return v, nrow, ncol, None, None, False


def write_svm(
    object: Mapping[str, Any],
    svm_file: str = "Rdata.svm",
    scale_file: str = "Rdata.scale",
    yscale_file: str = "Rdata.yscale",
) -> None:
    """Write ``object`` in libsvm text format and optional scaling tables."""
    coefs = object.get("coefs")
    if coefs is None:
        raise ValueError("object has no support vectors to write")
    coefs_vec = np.ascontiguousarray(coefs, dtype=float).reshape(-1, order="F")

    v, sv_nr, sv_nc, rowindex, colindex, sparse = _support_vector_arrays(object)
    rho = np.ascontiguousarray(object["rho"], dtype=float)
    labels = np.ascontiguousarray(object["labels"], dtype=np.int32)
    nsv = np.ascontiguousarray(object["nSV"], dtype=np.int32)
    compprob = bool(object.get("compprob", False))
    prob_a = object.get("probA")
    prob_b = object.get("probB")

    svmwrite_model = _svmwrite_ext()
    kwargs: dict[str, Any] = {
        "sv": v,
        "coefs": coefs_vec,
        "rho": rho,
        "tot_nsv": int(object["tot.nSV"]),
        "sv_nc": int(sv_nc),
        "nclasses": int(object["nclasses"]),
        "labels": labels,
        "nsv": nsv,
        "svm_type": int(object["type"]),
        "kernel_type": int(object["kernel"]),
        "degree": int(object["degree"]),
        "gamma": float(object["gamma"]),
        "coef0": float(object["coef0"]),
        "compprob": compprob,
        "sparse_model": sparse,
        "filename": svm_file,
    }
    if compprob:
        kwargs["prob_a"] = np.ascontiguousarray(prob_a, dtype=float)
        kwargs["prob_b"] = np.ascontiguousarray(prob_b, dtype=float)
    if sparse:
        kwargs["rowindex"] = rowindex
        kwargs["colindex"] = colindex

    svmwrite_model(**kwargs)

    x_scale = object.get("x.scale")
    if x_scale is None:
        raise ValueError('object$x.scale is required for the scale file')
    _write_scale_table(
        scale_file,
        x_scale["scaled:center"],
        x_scale["scaled:scale"],
    )

    y_scale = object.get("y.scale")
    if y_scale is not None:
        _write_scale_table(
            yscale_file,
            [y_scale["scaled:center"]],
            [y_scale["scaled:scale"]],
        )
