"""Progress-bar apply."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from pbapply.pblapply import pblapply


def pbapply(
    X: Any,
    MARGIN: int | Sequence[int] | str | Sequence[str],
    FUN: Callable[..., Any],
    *args: Any,
    simplify: bool = True,
    cl: Any = None,
    **kwargs: Any,
) -> Any:
    """Apply FUN over margins of X with progress reporting via pblapply."""
    if not callable(FUN):
        raise TypeError("FUN must be callable")
    simplify = bool(simplify)

    array, dimnames = _as_array(X)
    dl = len(array.shape)
    if dl == 0:
        raise ValueError("dim(X) must have a positive length")

    margin = _margin_indices(MARGIN, dl, dimnames)
    d = list(array.shape)
    ds = list(range(dl))
    d_call = [d[axis] for axis in ds if axis not in margin]
    d_ans = [d[axis] for axis in margin]
    dn_call = _slice_dimnames(dimnames, [axis for axis in ds if axis not in margin])
    dn_ans = _slice_dimnames(dimnames, margin)

    d2 = math.prod(d_ans) if d_ans else 1
    if d2 == 0:
        new_x = np.zeros((max(1, math.prod(d_call) if d_call else 1), 1), dtype=array.dtype)
        slice_arg = (
            new_x[:, 0]
            if len(d_call) < 2
            else new_x[:, 0].reshape(d_call, order="F")
        )
        ans = FUN(slice_arg, *args, **kwargs)
        if ans is None:
            return None
        if len(d_ans) < 2:
            if isinstance(ans, np.ndarray):
                flat = ans.reshape(-1)
                return flat[0] if flat.size else ans
            if isinstance(ans, Sequence) and not isinstance(ans, (str, bytes)):
                return ans[0] if len(ans) else ans
            return ans
        return np.asarray(ans).reshape(d_ans, order="F")

    s_call = [axis for axis in ds if axis not in margin]
    s_ans = margin
    perm = s_call + s_ans
    new_x = np.transpose(array, perm)
    new_x = new_x.reshape((max(1, math.prod(d_call)), d2), order="F")

    if len(d_call) < 2:
        arglist = [new_x[:, index] for index in range(d2)]
        if dn_call:
            _attach_column_dimnames(arglist, dn_call)
    else:
        arglist = [
            new_x[:, index].reshape(d_call, order="F") for index in range(d2)
        ]

    ans = pblapply(arglist, FUN, *args, cl=cl, **kwargs)
    return _reshape_apply_answer(
        ans,
        simplify=simplify,
        d_ans=d_ans,
        dn_ans=dn_ans,
        d2=d2,
        margin=margin,
        d_call=d_call,
        dn_call=dn_call,
    )


def _as_array(x: Any) -> tuple[np.ndarray, list[list[str] | None] | None]:
    if isinstance(x, np.ndarray):
        array = np.asarray(x)
        if array.dtype.names:
            array = array.view(np.ndarray)
        elif array.ndim == 2 and _has_matrix_class(x):
            array = np.asarray(array, dtype=float, order="F")
        else:
            array = np.asarray(array, order="F")
        return array, _dimnames(x)
    array = np.asarray(x, order="F")
    if array.ndim == 0:
        raise ValueError("dim(X) must have a positive length")
    return array, _dimnames(x)


def _has_matrix_class(x: Any) -> bool:
    klass = getattr(x, "__class__", type(x))
    return klass is np.ndarray


def _dimnames(x: Any) -> list[list[str] | None] | None:
    dn = getattr(x, "dimnames", None)
    if dn is not None:
        return [list(level) if level is not None else None for level in dn]
    return None


def _margin_indices(
    margin: int | Sequence[int] | str | Sequence[str],
    rank: int,
    dimnames: list[list[str] | None] | None,
) -> list[int]:
    if isinstance(margin, str):
        margin = [margin]
    if isinstance(margin, Sequence) and margin and isinstance(margin[0], str):
        dnn = getattr(dimnames, "names", None) if dimnames is not None else None
        if dnn is None and isinstance(dimnames, list):
            dnn = getattr(dimnames, "names", None)
        if not dnn:
            raise ValueError("'X' must have named dimnames")
        dnn = list(dnn)
        resolved: list[int] = []
        for label in margin:
            try:
                index = dnn.index(label)
            except ValueError as exc:
                raise ValueError(
                    "not all elements of 'MARGIN' are names of dimensions"
                ) from exc
            resolved.append(index)
        return resolved
    if isinstance(margin, int):
        return [margin - 1]
    return [int(item) - 1 for item in margin]


def _dimension_names(dimnames: list[list[str] | None] | None, rank: int) -> list[str]:
    if dimnames is None:
        return [""] * rank
    labels: list[str] = []
    for axis in range(rank):
        if axis < len(dimnames) and dimnames[axis]:
            labels.append(str(dimnames[axis][0]))
        else:
            labels.append("")
    return labels


def _slice_dimnames(
    dimnames: list[list[str] | None] | None, axes: Sequence[int]
) -> list[list[str] | None] | None:
    if dimnames is None:
        return None
    return [dimnames[axis] if axis < len(dimnames) else None for axis in axes]


def _attach_column_dimnames(arglist: list[Any], dn_call: list[list[str] | None]) -> None:
    if not dn_call or not dn_call[0]:
        return
    names = dn_call[0]
    for item in arglist:
        try:
            item.names = list(names)  # type: ignore[attr-defined]
        except AttributeError:
            break


def _reshape_apply_answer(
    ans: list[Any],
    *,
    simplify: bool,
    d_ans: list[int],
    dn_ans: list[list[str] | None] | None,
    d2: int,
    margin: list[int],
    d_call: list[int],
    dn_call: list[list[str] | None] | None,
) -> Any:
    if not ans:
        return ans
    first = ans[0]
    ans_list = not simplify or _is_recursive(first)
    l_ans = _length(first)
    ans_names = _names(first)
    if not ans_list:
        ans_list = any(_length(item) != l_ans for item in ans)
    if not ans_list and ans_names:
        if not all(_names(item) == ans_names for item in ans):
            ans_names = None
    if ans_list:
        len_a = d2
        flat = ans
    else:
        flat = _unlist(ans)
        len_a = len(flat)
    if len(margin) == 1 and len_a == d2:
        names = None
        if dn_ans and dn_ans[0]:
            names = dn_ans[0]
        return _with_names(flat, names)
    if len_a == d2:
        return np.asarray(flat, dtype=object).reshape(d_ans, order="F")
    if len_a and len_a % d2 == 0:
        if dn_ans is None:
            dn_ans = [None] * len(d_ans)
        dn1: list[list[str] | None] = [[name for name in (ans_names or [])]]
        if dn_call and dn_call[0] and ans_names and len(ans_names) == len(dn_call[0]):
            dn1[0] = list(dn_call[0])
        merged = dn1 + (dn_ans or [])
        return np.asarray(flat, dtype=object).reshape((len_a // d2, *d_ans), order="F")
    return flat


def _is_recursive(value: Any) -> bool:
    if isinstance(value, (list, tuple, dict, np.ndarray)):
        if isinstance(value, np.ndarray) and value.ndim == 0:
            return False
        if isinstance(value, np.ndarray) and value.size <= 1:
            return False
        return isinstance(value, (list, tuple, dict)) or (
            isinstance(value, np.ndarray) and value.dtype == object
        )
    return False


def _length(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, np.ndarray):
        return int(value.size)
    if isinstance(value, (str, bytes)):
        return len(value)
    try:
        return len(value)
    except TypeError:
        return 1


def _names(value: Any) -> list[str | None] | None:
    names = getattr(value, "names", None)
    if names is None:
        return None
    return list(names)


def _unlist(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    for item in values:
        if isinstance(item, np.ndarray):
            out.extend(item.reshape(-1).tolist())
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            out.extend(item)
        else:
            out.append(item)
    return out


def _with_names(values: Any, names: list[str] | None) -> Any:
    if names is None:
        return values
    arr = np.asarray(values, dtype=float)
    result = arr.reshape(-1)
    try:
        result.names = list(names)  # type: ignore[attr-defined]
    except AttributeError:
        pass
    return result
