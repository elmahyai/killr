"""Block-diagonal positive-definite structure (nlme ``pdBlocked`` and ``pdConstruct.pdBlocked``)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from nlme.pdconstruct import pdConstruct, resolve_value
from nlme.pdfactor import PdBlocked
from nlme.pdmat import PdMat


def pdBlocked(
    value: Any = (),
    form: Any = None,
    nam: Any = None,
    data: Any = None,
    pdClass: Any = "pdSymm",
) -> PdBlocked:
    """Construct a ``pdBlocked`` object: one ``pdMat`` per block of names.

    ``nam`` is a list with one name vector per block. ``pdClass`` is one class
    name, or one class per block.
    """
    return _build(value, form, nam, data, pdClass)


def construct_pd_blocked(object: PdBlocked, value: Any, form: Any, nam: Any, data: Any) -> PdBlocked:
    """``pdConstruct.pdBlocked`` for an existing object: its block classes are reused."""
    pd_class = [block.pd_class for block in object.blocks]
    return _build(value, form, nam, data, pd_class)


def _build(value: Any, form: Any, nam: Any, data: Any, pd_class: Any) -> PdBlocked:
    if isinstance(value, (PdMat, PdBlocked)) or (
        isinstance(value, (list, tuple)) and value and not _is_number_list(value)
    ):
        raise NotImplementedError("constructing pdBlocked from a list of pdMat objects is not translated")

    nam_list = list(nam) if nam is not None else None
    form_list = list(form) if form is not None else None
    if isinstance(pd_class, (list, tuple)):
        classes = list(pd_class)
    else:
        classes = None
    n_form = len(form_list) if form_list is not None else 0
    n_nam = len(nam_list) if nam_list is not None else 0
    n_pd = len(classes) if classes is not None else 1
    n_blocks = max(n_form, n_nam, n_pd)
    if n_blocks == 1:
        raise ValueError("None of the arguments specify more than one block")
    if classes is None:
        classes = [pd_class] * n_blocks

    blocks: list[PdMat] = []
    for index in range(n_blocks):
        names_i = nam_list[index] if nam_list is not None and index < n_nam else None
        form_i = form_list[index] if form_list is not None and index < n_form else None
        blocks.append(
            pdConstruct(PdMat(values=np.empty(0), pd_class=classes[index]), (), form_i, names_i, data)
        )

    names_list = [tuple(block.names) for block in blocks]
    lengths = [len(names) for names in names_list]
    if not all(lengths):
        if not any(lengths):
            raise NotImplementedError("pdBlocked without names is not translated")
        raise ValueError("all elements must have names when any has names")
    all_names = tuple(name for names in names_list for name in names)
    if len(set(all_names)) != len(all_names):
        raise ValueError('cannot have duplicated column names in a "pdMat" object')

    obj = PdBlocked(
        blocks=tuple(blocks),
        names_list=tuple(names_list),
        dimnames=(all_names, all_names),
        pd_class="pdBlocked",
    )
    plen = [_unconstrained_length(block) for block in obj.blocks]
    if not all(plen):
        raise ValueError("all elements must have a non-zero size")

    if isinstance(value, (list, tuple)) and len(value) == 0:
        return obj
    if isinstance(value, np.ndarray) and value.ndim == 2:
        return _matrix_init(obj, value)
    if _is_number_list(value) and np.asarray(value).size > 0:
        return _coef_init(obj, value, plen)
    return obj


def _matrix_init(obj: PdBlocked, value: np.ndarray) -> PdBlocked:
    side = sum(len(names) for names in obj.names_list)
    mat = np.asarray(value, dtype=np.float64)
    if mat.shape != (side, side):
        raise ValueError("cannot change the number of columns on an initialized object")
    new_blocks = []
    offset = 0
    for block in obj.blocks:
        size = len(block.names)
        sub = mat[offset : offset + size, offset : offset + size]
        new_blocks.append(pdConstruct(block, sub))
        offset += size
    return replace(obj, blocks=tuple(new_blocks))


def _coef_init(obj: PdBlocked, value: Any, plen: list[int]) -> PdBlocked:
    flat = np.asarray(value, dtype=np.float64).ravel()
    if flat.size != sum(plen):
        raise ValueError('cannot change parameter length of initialized "pdMat" object')
    new_blocks = []
    start = 0
    for block, size in zip(obj.blocks, plen, strict=True):
        new_blocks.append(pdConstruct(block, flat[start : start + size]))
        start += size
    return replace(obj, blocks=tuple(new_blocks))


def _unconstrained_length(block: PdMat) -> int:
    """Length of ``coef(block, TRUE)`` for an identity-initialized block."""
    n = len(block.names)
    cls = block.pd_class
    if cls == "pdDiag":
        return n
    if cls == "pdIdent":
        return 1
    if cls == "pdCompSymm":
        return 2
    if cls in ("pdLogChol", "pdSymm"):
        return n * (n + 1) // 2
    raise NotImplementedError(f"pdBlocked with class {cls!r} is not translated")


def _is_number_list(value: Any) -> bool:
    if isinstance(value, np.ndarray):
        return value.ndim <= 1 and value.dtype.kind in "biuf"
    if isinstance(value, (int, float, np.number)):
        return True
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, (int, float, np.number)) for item in value)
    return False
