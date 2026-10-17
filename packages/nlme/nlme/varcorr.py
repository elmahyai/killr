"""Variance and correlation components from mixed models (nlme ``VarCorr``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

_MISSING = object()


@dataclass(slots=True)
class PdMat:
    """Minimal ``pdMat`` stand-in for ``VarCorr`` (correlation matrix storage)."""

    corr: np.ndarray
    std_dev: tuple[float, ...]
    std_dev_names: tuple[str, ...]
    formula: str = "~1"
    no_correlation: bool = False
    pd_class: str = "pdLogChol"
    classes: tuple[str, ...] = ("pdLogChol", "pdSymm", "pdMat")


@dataclass(slots=True)
class PdBlocked:
    """Block-diagonal ``pdBlocked`` stand-in as a sequence of ``PdMat`` blocks."""

    blocks: tuple[PdMat, ...]
    classes: tuple[str, ...] = ("pdBlocked", "pdMat")


@dataclass(slots=True)
class ReStruct:
    """Named random-effects structures on an ``lme`` stand-in."""

    items: tuple[tuple[str, PdMat | PdBlocked], ...]


@dataclass(slots=True)
class ModelStruct:
    reStruct: ReStruct


@dataclass(slots=True)
class Lme:
    """``lme`` stand-in carrying ``sigma`` and ``modelStruct`` for ``VarCorr``."""

    modelStruct: ModelStruct
    sigma: float
    classes: tuple[str, ...] = ("lme",)


@dataclass(frozen=True, slots=True)
class SummaryPdMat:
    """``summary.pdMat`` object: correlation matrix plus metadata."""

    values: np.ndarray
    std_dev: np.ndarray
    no_correlation: bool
    formula: str
    struct_name: str


@dataclass(frozen=True, slots=True)
class VarCorrResult:
    """Formatted ``VarCorr.lme`` matrix with optional title."""

    values: np.ndarray
    rownames: tuple[str, ...]
    colnames: tuple[str, ...]
    title: str | None = None
    classes: tuple[str, ...] = ("VarCorr.lme",)


def summary(object, **_ignored) -> SummaryPdMat:
    """Correlation matrix summary for a ``pdMat`` stand-in."""
    if isinstance(object, PdMat):
        return SummaryPdMat(
            np.array(object.corr, dtype=np.float64, copy=True),
            np.asarray(object.std_dev, dtype=np.float64),
            object.no_correlation,
            object.formula,
            object.pd_class,
        )
    raise TypeError(f"no applicable method for 'summary' applied to object of type {type(object)!r}")


def VarCorr(x, sigma=_MISSING, rdig: int = 3, **kwargs):
    """Extract variance and correlation components (``VarCorr`` generic)."""
    del kwargs
    classes = _class_vector(x)
    if "lme" in classes:
        use_sigma = x.sigma if sigma is _MISSING else float(sigma)
        return _var_corr_lme(x, sigma=use_sigma, rdig=rdig)
    use_sigma = 1.0 if sigma is _MISSING else float(sigma)
    if "pdBlocked" in classes:
        return _var_corr_pd_blocked(x, sigma=use_sigma, rdig=rdig)
    if "pdMat" in classes or any(name.startswith("pd") for name in classes):
        return _var_corr_pd_mat(x, sigma=use_sigma, rdig=rdig)
    shown = _show_classes(classes)
    raise TypeError(f"no applicable method for 'VarCorr' applied to an object of class {shown}")


def _var_corr_lme(x: Lme, sigma: float, rdig: int) -> VarCorrResult:
    re_items = list(reversed(x.modelStruct.reStruct.items))
    parts = [_var_corr_pd_mat(block, sigma=sigma, rdig=rdig) for _, block in re_items]
    names = [name for name, _ in re_items]
    count = len(parts)
    if count <= 1:
        block_name = names[0] if names else None
        part = parts[0]
        mm = np.vstack(
            (
                part.values.astype(np.float64, copy=False),
                np.array([[sigma**2, sigma]], dtype=np.float64),
            )
        )
        rownames = part.rownames + ("Residual",)
        colnames = part.colnames
        formatted = _format_block(mm, colnames)
        corr = part.corr
        if corr is not None:
            blank = np.array([[""] * corr.shape[1]], dtype=object)
            corr_block = np.vstack((corr, blank))
            formatted = np.column_stack((formatted, corr_block))
            extra_cols = corr.shape[1]
            colnames = colnames + ("Corr",) + ("",) * (extra_cols - 1)
        title = None
        if block_name is not None:
            title = f"{block_name} = {part.form_str}"
        return VarCorrResult(formatted, rownames, tuple(colnames), title)

    nrows = np.array([part.values.shape[0] for part in parts], dtype=np.intp)
    total_rows = int(np.sum(nrows) + count + 1)
    cor_parts = [part.corr for part in parts]
    has_null = [part is None for part in cor_parts]
    max_corr = 0
    if not all(has_null):
        max_corr = max(
            part.shape[1] for part, missing in zip(cor_parts, has_null, strict=True) if not missing
        )
    colnames = list(parts[0].colnames)
    if max_corr:
        colnames.extend(["Corr"] + [""] * (max_corr - 1))

    bd_rows = [part.values.astype(np.float64, copy=False) for part in parts]
    bd = np.vstack(bd_rows + [np.array([[sigma**2, sigma]], dtype=np.float64)])
    table = np.empty((total_rows, 2 + max_corr), dtype=object)
    table[:] = ""

    data_rows = _row_indices(nrows, count)
    table[data_rows, 0] = _format_real(bd[:, 0])
    table[data_rows, 1] = _format_real(bd[:, 1])

    title_rows = _title_rows(nrows, count)
    for index, part in enumerate(parts):
        table[title_rows[index], 0] = part.form_str

    rownames = [""] * (int(np.sum(nrows)) + count)
    for index, part in enumerate(parts):
        rownames[title_rows[index]] = f"{names[index]} ="
    start = 0
    for index, part in enumerate(parts):
        span = int(nrows[index])
        rownames[start : start + span] = list(part.rownames)
        if cor_parts[index] is not None:
            width = cor_parts[index].shape[1]
            table[start : start + span, 2 : 2 + width] = cor_parts[index]
        start += span + 1

    rownames.append("Residual")
    return VarCorrResult(
        table,
        tuple(rownames),
        tuple(colnames),
        None,
    )


def _var_corr_pd_blocked(x: PdBlocked, sigma: float, rdig: int) -> _PdMatVarCorr:
    blocks = [_var_corr_pd_mat(block, sigma=sigma, rdig=rdig) for block in x.blocks]
    bd = np.vstack([block.values.astype(np.float64, copy=False) for block in blocks])
    form_str = ", ".join(block.form_str for block in blocks)
    return _PdMatVarCorr(
        bd,
        blocks[0].rownames if blocks else (),
        blocks[0].colnames if blocks else ("Variance", "StdDev"),
        form_str,
        None,
    )


def _var_corr_pd_mat(x: PdMat, sigma: float, rdig: int) -> _PdMatVarCorr:
    sx = summary(x)
    sd = sigma * sx.std_dev
    var = sd**2
    names = x.std_dev_names
    sd_flat = np.asarray(sd, dtype=np.float64).ravel()
    var_flat = np.asarray(var, dtype=np.float64).ravel()
    matrix = np.column_stack((var_flat, sd_flat))
    form_str = _form_str(x)
    corr = None
    p = matrix.shape[0]
    if p >= 2 and not sx.no_correlation:
        corr = _format_corr(sx.values, names, rdig)
    return _PdMatVarCorr(matrix, names, ("Variance", "StdDev"), form_str, corr)


@dataclass(frozen=True, slots=True)
class _PdMatVarCorr:
    values: np.ndarray
    rownames: tuple[str, ...]
    colnames: tuple[str, ...]
    form_str: str
    corr: np.ndarray | None


def _format_block(matrix: np.ndarray, colnames: Sequence[str]) -> np.ndarray:
    out = np.empty(matrix.shape, dtype=object)
    out[:, 0] = _format_real(matrix[:, 0])
    out[:, 1] = _format_real(matrix[:, 1])
    return out


def _format_corr(corr: np.ndarray, names: Sequence[str], rdig: int) -> np.ndarray:
    p = corr.shape[0]
    sx = np.empty((p, p), dtype=object)
    sx[:, :] = corr
    ll = np.tril(np.ones((p, p), dtype=bool), k=-1)
    flat = sx[ll]
    formatted = [format(round(float(value), rdig)) for value in flat]
    sx[ll] = formatted
    sx[~ll] = ""
    if p:
        sx[0, :] = _abbreviate(tuple(str(name) for name in names), rdig + 3)
    colnames = ["Corr"] + [""] * (p - 1)
    return sx[:, : p - 1 if p else 0]


def _form_str(x: PdMat) -> str:
    formula = x.formula
    if isinstance(formula, list):
        pieces = [str(part) for part in formula]
        return f"{x.pd_class}(list({','.join(pieces)}))"
    deparsed = str(formula)
    if deparsed.startswith("~"):
        deparsed = deparsed[1:]
    return f"{x.pd_class}({deparsed})"


def _row_indices(nrows: np.ndarray, count: int) -> np.ndarray:
    total = int(np.sum(nrows) + count + 1)
    title_rows = 1 + np.concatenate(([0], np.cumsum(nrows + 1)[:-1]))
    data_rows = np.ones(total, dtype=bool)
    data_rows[title_rows] = False
    return np.nonzero(data_rows)[0]


def _title_rows(nrows: np.ndarray, count: int) -> np.ndarray:
    return 1 + np.concatenate(([0], np.cumsum(nrows + 1)[:-1]))


def _class_vector(object: Any) -> tuple[str, ...]:
    classes = getattr(object, "classes", None)
    if classes is None:
        classes = getattr(object, "__class__", type(object)).__name__
    if isinstance(classes, str):
        return (classes,)
    return tuple(str(name) for name in classes)


def _show_classes(classes: Sequence[str]) -> str:
    quoted = [f'"{name}"' for name in classes]
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f"{quoted[0]} and {quoted[1]}"
    return ", ".join(quoted[:-1]) + f", and {quoted[-1]}"


def _format_real(values: Sequence[float]) -> list[str]:
    numbers = [float(value) for value in values]
    if not numbers:
        return []
    neg = 0
    mnl = 10**9
    mxl = rgt = mxsl = mxns = -(10**9)
    any_finite = False
    naflag = False
    digits = 7
    for value in numbers:
        if not np.isfinite(value):
            if np.isnan(value):
                naflag = True
            continue
        any_finite = True
        negative, power, significant, widens = _scientific(value, digits)
        left = power + 1
        if widens:
            left -= 1
        sleft = negative + (1 if left <= 0 else left)
        right = significant - left
        if negative:
            neg = 1
        rgt = max(rgt, right)
        mxl = max(mxl, left)
        mnl = min(mnl, left)
        mxsl = max(mxsl, sleft)
        mxns = max(mxns, significant)
    if not any_finite:
        width = 2
        return ["NA".rjust(width) if np.isnan(value) else "Inf" for value in numbers]
    if mxl < 0:
        mxsl = 1 + neg
    if rgt < 0:
        rgt = 0
    width_fixed = mxsl + rgt + (1 if rgt != 0 else 0)
    exponent_digits = 2 if (mxl > 100 or mnl <= -99) else 1
    decimals = mxns - 1
    width_scientific = neg + (1 if decimals > 0 else 0) + decimals + 4 + exponent_digits
    if width_fixed <= width_scientific:
        width = width_fixed
        places = rgt
        scientific = False
    else:
        width = width_scientific
        places = decimals
        scientific = True
    if naflag and width < 2:
        width = 2
    rendered = []
    for value in numbers:
        if np.isnan(value):
            rendered.append("NA".rjust(width))
        elif scientific:
            rendered.append(f"{value:.{places}e}".rjust(width))
        else:
            rendered.append(f"{value:.{places}f}".rjust(width))
    return rendered


def _scientific(value: float, digits: int) -> tuple[int, int, int, bool]:
    negative = int(value < 0)
    magnitude = abs(value)
    if magnitude == 0.0:
        return negative, 0, 1, False
    power = int(np.floor(np.log10(magnitude)))
    scaled = magnitude / 10.0**power
    rounded = round(scaled, digits - 1)
    widens = False
    if rounded >= 10.0:
        rounded = 1.0
        power += 1
        widens = True
    text = f"{rounded:.{digits - 1}f}".replace(".", "").rstrip("0")
    significant = max(len(text), 1)
    return negative, power, significant, widens


def _abbreviate(names: Sequence[str], minlength: int) -> list[str]:
    cleaned = [str(name).strip() for name in names]
    if minlength <= 0:
        return [""] * len(cleaned)
    length = minlength
    while True:
        out = [_abbrev_one(name, length) for name in cleaned]
        if len(set(out)) == len(out):
            return out
        length += 1


def _abbrev_one(name: str, minlength: int) -> str:
    if len(name) <= minlength:
        return name
    vowels = set("aeiouAEIOU")
    picked = [name[0]]
    for char in name[1:]:
        if len(picked) >= minlength:
            break
        if char not in vowels:
            picked.append(char)
    index = 1
    while len(picked) < minlength and index < len(name):
        if name[index] not in picked:
            picked.append(name[index])
        index += 1
    return "".join(picked[:minlength])
