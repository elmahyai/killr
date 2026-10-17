"""Random effects structure constructor (nlme reStruct)."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

_PD_CLASS_ORDER = ("pdSymm", "pdDiag", "pdIdent", "pdCompSymm", "pdLogChol")


@dataclass(slots=True)
class PdMatElement:
    """Minimal ``pdMat`` storage used by ``reStruct``."""

    values: np.ndarray
    formula: str
    names: tuple[str, ...]
    pd_class: str = "pdLogChol"

    @property
    def classes(self) -> tuple[str, ...]:
        if self.pd_class == "pdLogChol":
            return (self.pd_class, "pdSymm", "pdMat")
        return (self.pd_class, "pdMat")


@dataclass(slots=True)
class ReStruct:
    """Random-effects structure: ordered ``pdMat`` blocks plus optimizer settings."""

    blocks: list[tuple[str, PdMatElement]]
    settings: np.ndarray
    plen: np.ndarray | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("reStruct",)

    def __len__(self) -> int:
        return len(self.blocks)

    def __getitem__(self, key: int | slice) -> PdMatElement | ReStruct:
        if isinstance(key, slice):
            subset = self.blocks[key]
            return ReStruct(list(subset), self.settings.copy(), self.plen)
        return self.blocks[key][1]

    @property
    def names(self) -> list[str]:
        return [name for name, _ in self.blocks]

    def items(self) -> list[tuple[str, PdMatElement]]:
        return list(self.blocks)


def reStruct(
    object: Any,
    pdClass: str = "pdLogChol",
    REML: bool = False,
    data: Mapping[str, Sequence[Any]] | None = None,
) -> ReStruct:
    """Construct a random-effects structure from formulas, ``pdMat`` objects, or another ``reStruct``."""
    if isinstance(object, ReStruct):
        settings = object.settings.copy()
        settings[0] = int(bool(REML))
        blocks = [
            (name, _pd_mat(element, pdClass=pdClass, data=data))
            for name, element in object.blocks
        ]
        return _finalize_restruct(blocks, settings, object.plen)

    if _is_formula(object):
        blocks = _blocks_from_formula(object, data)
    elif isinstance(object, PdMatElement):
        if not object.formula:
            raise ValueError('"pdMat" element must have a formula')
        blocks = [("", object)]
    elif isinstance(object, (list, dict)):
        blocks = _blocks_from_list(object, data)
    else:
        raise ValueError("'object' must be a list or a formula")

    elements = [_pd_mat(element, pdClass=pdClass, data=data) for _, element in blocks]
    blocks = [(blocks[i][0], elements[i]) for i in range(len(blocks))]
    blocks.reverse()
    return _finalize_restruct(blocks, _default_settings(REML, elements), None)


def is_initialized(object: PdMatElement | ReStruct) -> bool:
    """Return whether a ``pdMat`` or ``reStruct`` object has assigned parameters."""
    if isinstance(object, ReStruct):
        return all(is_initialized(element) for _, element in object.blocks)
    return int(object.values.size) > 0


def Names(object: PdMatElement | str, data: Mapping[str, Sequence[Any]] | None = None) -> tuple[str, ...]:
    """Column names for a ``pdMat`` formula or object."""
    if isinstance(object, PdMatElement):
        return object.names
    return _names_formula(_formula_text(object), data)


def Dim(object: PdMatElement) -> tuple[int, int]:
    """Square dimension of a ``pdMat`` object."""
    side = len(object.names)
    return side, side


def matrix(object: PdMatElement, unconstrained: bool = False) -> np.ndarray:
    """Extract the matrix representation of a ``pdMat`` object."""
    if unconstrained or not is_initialized(object):
        return np.empty((0, 1), dtype=np.float64)
    side = len(object.names)
    return np.asarray(object.values, dtype=np.float64).reshape(side, side)


def coef(object: PdMatElement, unconstrained: bool = True) -> np.ndarray:
    """Extract coefficients from a ``pdMat`` object."""
    del unconstrained
    if not is_initialized(object):
        return np.array([], dtype=np.float64)
    return np.asarray(object.values, dtype=np.float64).ravel()


def formula(object: PdMatElement, asList: bool = False) -> str | list[str]:
    """Return the one-sided formula stored in a ``pdMat`` object."""
    del asList
    return object.formula


def _finalize_restruct(
    blocks: list[tuple[str, PdMatElement]],
    settings: np.ndarray,
    plen: np.ndarray | None,
) -> ReStruct:
    if plen is None and blocks and all(is_initialized(element) for _, element in blocks):
        lengths = np.array([coef(element).size for _, element in blocks], dtype=np.int64)
        plen = lengths
    return ReStruct(blocks=blocks, settings=settings, plen=plen)


def _default_settings(remel: bool, elements: Sequence[PdMatElement]) -> np.ndarray:
    codes = [_pd_class_code(element.pd_class) for element in elements]
    return np.array([int(bool(remel)), 1, 0, *codes], dtype=np.int64)


def _pd_class_code(pd_class: str) -> int:
    try:
        return _PD_CLASS_ORDER.index(pd_class)
    except ValueError:
        return -1


def _blocks_from_formula(formula_obj: Any, data: Mapping[str, Sequence[Any]] | None) -> list[tuple[str, str]]:
    text = _formula_text(formula_obj)
    grp_form = _get_groups_formula(text, as_list=True)
    if grp_form is None:
        return [("", text)]
    if _formula_lhs(text):
        response = _get_response_rhs(text)
        covariate = _get_covariate_rhs(text)
        text = f"{response}~{covariate}"
    else:
        text = _get_covariate_formula(text)
    return [(name, text) for name in grp_form]


def _blocks_from_list(
    object: list[Any] | dict[str, Any],
    data: Mapping[str, Sequence[Any]] | None,
) -> list[tuple[str, Any]]:
    if isinstance(object, dict):
        named = list(object.items())
    elif not object:
        named = []
    elif all(_is_formula(entry) for entry in object) and all(_formula_length(entry) == 3 for entry in object):
        named = [("", object)]
    else:
        named = [(str(index), entry) for index, entry in enumerate(object)]

    blocks: list[tuple[str, Any]] = []
    grp_names: list[str] = []
    for name, element in named:
        normalized = _normalize_list_element(element, data)
        if isinstance(normalized, _FormulaWithGroup):
            if not name:
                name = normalized.grp_name
            grp_names.append(name)
        blocks.append((name, normalized))

    if grp_names:
        for index, (name, element) in enumerate(blocks):
            if not name and index < len(grp_names):
                blocks[index] = (grp_names[index], element)
    return blocks


def _normalize_list_element(element: Any, data: Mapping[str, Sequence[Any]] | None) -> Any:
    if isinstance(element, PdMatElement):
        if not element.formula:
            raise ValueError('"pdMat" elements must have a formula')
        return element
    if _is_formula(element):
        grp_form = _get_groups_formula(_formula_text(element), as_list=False)
        if grp_form is not None:
            covariate = _get_covariate_formula(_formula_text(element))
            return _FormulaWithGroup(covariate, _group_name_from_formula(grp_form))
        return element
    if isinstance(element, list) and element and all(_is_formula(item) and _formula_length(item) == 3 for item in element):
        return element
    raise ValueError('elements in \'object\' must be formulas or "pdMat" objects')


@dataclass(slots=True)
class _FormulaWithGroup:
    formula: str
    grp_name: str


def _pd_mat(
    value: Any,
    pdClass: str = "pdLogChol",
    data: Mapping[str, Sequence[Any]] | None = None,
) -> PdMatElement:
    if isinstance(value, PdMatElement):
        if is_initialized(value):
            return _pd_mat_from_matrix(value, pdClass, data)
        return _pd_mat_from_formula(value.formula, value.names, pdClass, data)
    if isinstance(value, _FormulaWithGroup):
        element = _pd_mat_from_formula(value.formula, (), pdClass, data)
        if value.grp_name:
            return element
        return element
    if _is_formula(value):
        return _pd_mat_from_formula(_formula_text(value), (), pdClass, data)
    if isinstance(value, np.ndarray):
        return _pd_mat_from_matrix_values(value, pdClass, data)
    raise TypeError(f"{value!r} is not a valid object for \"pdMat\"")


def _pd_mat_from_matrix(element: PdMatElement, pdClass: str, data: Mapping[str, Sequence[Any]] | None) -> PdMatElement:
    side = len(element.names)
    matrix_values = matrix(element)
    return _pd_mat_from_matrix_values(matrix_values, pdClass, data, formula=element.formula, names=element.names)


def _pd_mat_from_matrix_values(
    value: np.ndarray,
    pdClass: str,
    data: Mapping[str, Sequence[Any]] | None,
    formula: str = "",
    names: tuple[str, ...] = (),
) -> PdMatElement:
    del data
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError("'value' must be a square matrix")
    if not names:
        names = tuple(f"V{index + 1}" for index in range(array.shape[0]))
    chol = np.linalg.cholesky((array + array.T) / 2.0)
    return PdMatElement(np.asarray(chol, dtype=np.float64).ravel(), formula, names, pdClass)


def _pd_mat_from_formula(
    form: str,
    names: tuple[str, ...],
    pdClass: str,
    data: Mapping[str, Sequence[Any]] | None,
) -> PdMatElement:
    if not names:
        names = _names_formula(form, data)
    return PdMatElement(np.array([], dtype=np.float64), form, names, pdClass)


def _names_formula(form: str, data: Mapping[str, Sequence[Any]] | None) -> tuple[str, ...]:
    _, columns = _model_matrix(form, data or {})
    return tuple(columns)


def _model_matrix(form: str, data: Mapping[str, Sequence[Any]]) -> tuple[int, list[str]]:
    text = _formula_text(form)
    if not text.startswith("~"):
        raise ValueError("formula must be one-sided")
    rhs = text[1:].strip()
    if rhs in ("1", "0"):
        rows = _nrows(data)
        return rows, ["(Intercept)"]
    terms = _split_terms(rhs)
    columns: list[str] = ["(Intercept)"]
    arrays: list[np.ndarray] = [np.ones(_nrows(data), dtype=np.float64)]
    for term in terms:
        if term == "1":
            continue
        if term == "-1" or term == "0":
            columns = []
            arrays = []
            continue
        if term not in data:
            raise KeyError(term)
        values = np.asarray(data[term], dtype=np.float64)
        columns.append(term)
        arrays.append(values)
    if not columns:
        return _nrows(data), []
    matrix = np.column_stack(arrays)
    return matrix.shape[0], columns


def _split_terms(rhs: str) -> list[str]:
    parts = [part.strip() for part in rhs.split("+")]
    return [part for part in parts if part]


def _nrows(data: Mapping[str, Sequence[Any]]) -> int:
    for values in data.values():
        return len(values)
    return 0


def _formula_text(form: Any) -> str:
    if isinstance(form, _FormulaWithGroup):
        return form.formula
    if hasattr(form, "formula"):
        return str(form.formula)
    text = str(form).strip()
    if not text.startswith("~") and "~" in text:
        return f"~{text.split('~', 1)[1].strip()}"
    return text


def _is_formula(form: Any) -> bool:
    if isinstance(form, _FormulaWithGroup):
        return True
    if isinstance(form, PdMatElement):
        return False
    text = str(form).strip()
    return text.startswith("~") or ("~" in text and "|" in text)


def _formula_length(form: Any) -> int:
    text = _formula_text(form)
    if "~" not in text:
        return 1
    lhs, rhs = text.split("~", 1)
    if "|" in rhs:
        return 3
    return 3 if lhs.strip() else 2


def _formula_lhs(text: str) -> str:
    if "~" not in text:
        return ""
    return text.split("~", 1)[0].strip()


def _get_response_rhs(text: str) -> str:
    lhs, _ = text.split("~", 1)
    return lhs.strip()


def _get_covariate_rhs(text: str) -> str:
    _, rhs = text.split("~", 1)
    if "|" in rhs:
        rhs = rhs.split("|", 1)[0]
    return rhs.strip()


def _get_covariate_formula(text: str) -> str:
    rhs = _get_covariate_rhs(text)
    return f"~{rhs}"


def _group_name_from_formula(formula_text: str) -> str:
    if "|" not in formula_text:
        return ""
    group = formula_text.split("|", 1)[1].strip()
    return group.split("/", 1)[0].strip()


def _get_groups_formula(text: str, as_list: bool) -> dict[str, str] | str | None:
    if "|" not in text:
        return None
    group = text.split("|", 1)[1].strip()
    levels = [part.strip() for part in group.split("/") if part.strip()]
    if not levels:
        return None
    if as_list:
        return {level: f"~{level}" for level in levels}
    return f"~{'/'.join(levels)}"


def load_pixel_csv(path: Path | str | None = None) -> dict[str, np.ndarray]:
    """Load the Pixel data frame columns used by the ``reStruct`` help example."""
    if path is None:
        path = Path(__file__).resolve().parents[1] / "proof" / "reStruct-pixel.csv"
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    columns: dict[str, list[Any]] = {key: [] for key in rows[0]}
    for row in rows:
        for key, value in row.items():
            if key in ("Dog", "Side"):
                columns[key].append(value)
            else:
                columns[key].append(float(value))
    return {key: np.asarray(values) for key, values in columns.items()}


def fingerprint_restruct(object: ReStruct) -> np.ndarray:
    """Numeric summary aligned with the proof scripts."""
    parts: list[float] = [float(value) for value in object.settings]
    parts.append(float(len(object)))
    parts.append(float(is_initialized(object)))
    for _, element in object.blocks:
        parts.append(float(is_initialized(element)))
    for _, element in object.blocks:
        parts.append(float(len(Names(element))))
    for _, element in object.blocks:
        parts.append(float(coef(element).size))
    for _, element in object.blocks:
        dim = Dim(element)
        parts.extend(float(value) for value in dim)
    for _, element in object.blocks:
        shape = matrix(element).shape
        parts.extend(float(value) for value in shape)
    return np.asarray(parts, dtype=np.float64)


def _pd_mat_for_factor(element: PdMatElement):
    """``PdMat`` view of a ``reStruct`` element, for ``pdFactor``."""
    from nlme.pdmat import PdMat

    return PdMat(
        values=np.asarray(element.values, dtype=np.float64),
        formula=element.formula,
        names=tuple(element.names),
        pd_class=element.pd_class,
        ncol=len(element.names),
    )


def _pd_factor_vector(object: ReStruct) -> np.ndarray:
    """``unlist(pdFactor(object))``: each block's factor, column-major, concatenated."""
    from nlme.pdfactor import pdFactor

    parts = [
        np.asarray(pdFactor(_pd_mat_for_factor(element)), dtype=np.float64).reshape(-1, order="F")
        for _, element in object.blocks
    ]
    return np.concatenate(parts) if parts else np.array([], dtype=np.float64)


def _pdims(dims: Mapping[str, Any]) -> list[int]:
    """``as.integer(unlist(conLin$dims))`` for the MEdims list, in R order."""
    values = [int(dims["N"]), int(dims["ZXrows"]), int(dims["ZXcols"]), int(dims["Q"]), int(dims["StrRows"])]
    for key in ("qvec", "ngrps", "DmOff", "ncol", "nrot"):
        values.extend(int(part) for part in np.asarray(dims[key]).reshape(-1))
    for key in ("ZXoff", "ZXlen", "SToff", "DecOff", "DecLen"):
        container = dims[key]
        parts = container.values() if isinstance(container, Mapping) else container
        for part in parts:
            values.extend(int(item) for item in np.asarray(part).reshape(-1))
    return values


def _xy_column_major(conlin: Any) -> np.ndarray:
    xy = np.asarray(conlin.Xy, dtype=np.float64)
    if xy.ndim == 1:
        return xy.reshape(-1)
    return np.asarray(xy, dtype=np.float64).reshape(-1, order="F")


def _aux_init(conlin: Any) -> list[np.ndarray]:
    """Diagonal starting values from ``Initialize.reStruct``'s ``auxInit``."""
    dims = conlin.dims
    q_levels = int(dims["Q"])
    qvec = np.asarray(dims["qvec"], dtype=np.int64).reshape(-1)[:q_levels]
    ngrps = np.asarray(dims["ngrps"], dtype=np.float64).reshape(-1)[:q_levels]
    n_rows = int(dims["N"])
    xy = _xy_column_major(conlin).reshape(n_rows, -1, order="F")
    total = int(qvec.sum())
    col_ss = np.sum(xy[:, :total] ** 2, axis=0)
    values = 0.375**2 * col_ss / np.repeat(ngrps, qvec)
    groups = np.repeat(np.arange(q_levels), qvec)
    return [np.diag(values[groups == level]) for level in range(q_levels)]


def _meem(object: ReStruct, conlin: Any, niter: int) -> ReStruct:
    """``MEEM``: ``niter`` EM iterations through the ``mixed_em`` kernel (nlmemixed)."""
    if niter <= 0:
        return object
    import nlmemixed
    from nlme.matrix_assign import matrix_assign

    dims = conlin.dims
    qvec = np.asarray(dims["qvec"], dtype=np.int64).reshape(-1)
    dm_off = np.asarray(dims["DmOff"], dtype=np.int64).reshape(-1)
    pd_cl = [0 if code == -1 else int(code) for code in object.settings[3:]]
    precvec = _pd_factor_vector(object)
    out = nlmemixed.mixed_em(
        _xy_column_major(conlin).tolist(),
        _pdims(dims),
        precvec.tolist(),
        int(niter),
        pd_cl,
        int(object.settings[0]),
        float(conlin.sigma),
    )
    updated = np.asarray(out[0], dtype=np.float64)
    blocks = []
    for index, (name, element) in enumerate(object.blocks):
        side = int(qvec[index])
        start = int(dm_off[index])
        block = updated[start : start + side * side].reshape(side, side, order="F")
        blocks.append((name, matrix_assign(element, block.T @ block)))
    return ReStruct(blocks=blocks, settings=object.settings.copy(), plen=object.plen)


def initialize(object: ReStruct, data: Any = None, conLin: Any = None, control: Mapping[str, Any] | None = None, **_ignored: Any) -> ReStruct:
    """Initialize a ``reStruct`` (R ``Initialize.reStruct``).

    Uninitialized blocks take the diagonal ``auxInit`` starting values, initialized
    blocks are inverted to precision form, and ``niterEM`` EM iterations refine
    them through ``mixed_em``. ``conLin`` is the condensed linear model.
    """
    from nlme.matrix_assign import matrix_assign, pd_matrix_from_params

    niter = int((control or {}).get("niterEM", 20))
    blocks: list[tuple[str, PdMatElement]] = []
    for name, element in object.blocks:
        if not element.names:
            element = _pd_mat_from_formula(element.formula, (), element.pd_class, data)
        blocks.append((name, element))
    plen_values = []
    for _, element in blocks:
        if is_initialized(element):
            plen_values.append(coef(element).size)
        else:
            plen_values.append(coef(matrix_assign(element, np.eye(len(element.names)))).size)
    if not all(value > 0 for value in plen_values):
        raise ValueError('all elements of a "reStruct" object must have a non-zero size')
    plen = np.asarray(plen_values, dtype=np.int64)
    initialized = [is_initialized(element) for _, element in blocks]
    if not all(initialized):
        if conLin is None:
            raise ValueError("conLin is required to initialize an uninitialized reStruct")
        aux = _aux_init(conLin)
    new_blocks: list[tuple[str, PdMatElement]] = []
    for index, (name, element) in enumerate(blocks):
        if initialized[index]:
            side = len(element.names)
            covariance = pd_matrix_from_params(element.pd_class, element.values, side)
            element = matrix_assign(element, np.linalg.inv(covariance))
        else:
            element = matrix_assign(element, aux[index])
        new_blocks.append((name, element))
    staged = ReStruct(blocks=new_blocks, settings=object.settings.copy(), plen=plen)
    return _meem(staged, conLin, niter)


def recalc_restruct(object: ReStruct, conLin: Any) -> Any:
    """``recalc.reStruct``: add ``logLik.reStruct`` (``mixed_loglik``) to ``conLin$logLik``."""
    import nlmemixed

    if not np.all(np.isfinite(_xy_column_major(conLin))):
        return replace(conLin, logLik=float(conLin.logLik) - np.inf)
    dims = conLin.dims
    settings = np.asarray(object.settings, dtype=np.int64)
    sigma = float(conLin.sigma)
    loglik_vec, lrss = nlmemixed.mixed_loglik(
        _xy_column_major(conLin).tolist(),
        _pdims(dims),
        _pd_factor_vector(object).tolist(),
        settings.tolist(),
        sigma,
    )
    loglik = float(loglik_vec[0])
    if sigma > 0 and int(settings[0]) == 1:
        n_rows = float(dims["N"])
        loglik = loglik + (n_rows * np.log(sigma) - np.exp(lrss) / (2.0 * sigma))
    return replace(conLin, logLik=float(conLin.logLik) + loglik)
