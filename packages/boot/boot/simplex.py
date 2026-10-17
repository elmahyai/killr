"""Two-phase tableau simplex, matching boot 1.3-32.

`simplex1` in R/bootfuns.q is internal. Two of its details are easy to
"correct" and then miss R: `1:n+m1+m2` is `(1:n)+m1+m2`, and the
artificial-variable cleanup iterates `seq_along(temp)` once because `temp`
is the last pivot scalar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

_DIGITS = 7
_WIDTH = 80
_SCIPEN = 0


@dataclass
class Simplex:
    """Result of simplex. basic indices are 1-based, as in R."""

    soln: np.ndarray
    solved: int
    value: float
    A: np.ndarray
    a: np.ndarray
    basic: np.ndarray
    maxi: bool
    obj: np.ndarray
    call: str
    slack: np.ndarray | None = None
    surplus: np.ndarray | None = None
    artificial: np.ndarray | None = None
    val_aux: float | None = None
    a_aux: np.ndarray | None = None


def simplex(
    a,
    A1=None,
    b1=None,
    A2=None,
    b2=None,
    A3=None,
    b3=None,
    maxi=False,
    n_iter=None,
    eps=1e-10,
):
    """Minimize a %*% x subject to A1 x <= b1, A2 x >= b2, A3 x = b3, x >= 0.

    maxi=True maximizes instead. A one-dimensional constraint is one row.
    n_iter defaults to n + 2 * (m1 + m2 + m3). eps is the equality tolerance.
    """

    objective = np.asarray(a, dtype=np.float64).reshape(-1).copy()
    n = int(objective.shape[0])
    A1m, m1 = _as_rows(A1, n, "A1")
    A2m, m2 = _as_rows(A2, n, "A2")
    A3m, m3 = _as_rows(A3, n, "A3")
    m = m1 + m2 + m3
    if n_iter is None:
        n_iter = n + 2 * m
    n_iter = int(n_iter)
    eps = float(eps)
    costs = -objective if maxi else objective.copy()
    call = _call_text(objective, A1, b1, A2, b2, A3, b3, maxi, n_iter, eps, n + 2 * m)

    if m2 + m3 == 0:
        out = _simplex1(
            np.concatenate([costs, np.zeros(m1)]),
            _cbind(A1m, _iden(m1)),
            _as_rhs(b1, m1, "b1"),
            [n + i for i in range(1, m1 + 1)],
            val=0.0,
            stage=2,
            n1=n + m1,
            eps=eps,
            n_iter=n_iter,
        )
    else:
        if m2 > 0:
            out = _simplex1(
                np.concatenate([costs, np.zeros(m1 + 2 * m2 + m3)]),
                _cbind(
                    _rbind(A1m, A2m, A3m),
                    _rbind(_iden(m1), _zero(m2 + m3, m1)),
                    _rbind(_zero(m1, m2), -_iden(m2) if m2 else None, _zero(m3, m2)),
                    _rbind(_zero(m1, m2 + m3), _iden(m2 + m3)),
                ),
                _as_rhs_cat(
                    [
                        (_as_rhs(b1, m1, "b1"), m1),
                        (_as_rhs(b2, m2, "b2"), m2),
                        (_as_rhs(b3, m3, "b3"), m3),
                    ]
                ),
                [n + i for i in range(1, m1 + 1)]
                + [n + m1 + m2 + i for i in range(1, m2 + m3 + 1)],
                val=0.0,
                stage=1,
                n1=n + m1 + m2,
                eps=eps,
                n_iter=n_iter,
            )
        else:
            out = _simplex1(
                np.concatenate([costs, np.zeros(m1 + m3)]),
                _cbind(_rbind(A1m, A3m), _iden(m1 + m3)),
                _as_rhs_cat([(_as_rhs(b1, m1, "b1"), m1), (_as_rhs(b3, m3, "b3"), m3)]),
                [n + i for i in range(1, m1 + m3 + 1)],
                val=0.0,
                stage=1,
                n1=n + m1,
                eps=eps,
                n_iter=n_iter,
            )
        if out["val_aux"] > eps:
            pass
        else:
            keep = n + m1 + m2
            out = _simplex1(
                out["a"][:keep],
                out["A"][:, :keep],
                out["soln"][np.asarray(out["basic"], dtype=int) - 1],
                list(out["basic"]),
                val=float(out["value"]),
                stage=2,
                n1=keep,
                eps=eps,
                n_iter=n_iter,
            )

    value = float(out["value"])
    if maxi:
        value = -value
    full = out["soln"]
    slack = full[n : n + m1].copy() if m1 > 0 else None
    surplus = full[n + m1 : n + m1 + m2].copy() if m2 > 0 else None
    artificial = None
    if out["solved"] == -1:
        # 1:n+m1+m2 is (1:n) + m1 + m2, not 1:(n+m1+m2).
        drop = {i + m1 + m2 for i in range(1, n + 1)}
        artificial = np.array(
            [full[i] for i in range(full.shape[0]) if (i + 1) not in drop],
            dtype=np.float64,
        )
    return Simplex(
        soln=full[:n].copy(),
        solved=int(out["solved"]),
        value=value,
        A=out["A"],
        a=out["a"],
        basic=np.asarray(out["basic"], dtype=int),
        maxi=bool(maxi),
        obj=objective,
        call=call,
        slack=slack,
        surplus=surplus,
        artificial=artificial,
        val_aux=out.get("val_aux"),
        a_aux=out.get("a_aux"),
    )


def print_simplex(x, **_unused):
    """Print a simplex solution and return that text.

    R returns the object invisibly. This returns the text so it can be
    compared. The objective value in the sentence uses R's as.character.
    The coefficient and solution lines use R's format with digits=7.
    """

    names = [f"x{i}" for i in range(1, len(x.obj) + 1)]
    parts = ["\nLinear Programming Results\n\n", "Call : ", x.call]
    if not x.call.endswith("\n"):
        parts.append("\n")
    parts.append("\nMaximization " if x.maxi else "\nMinimization ")
    parts.append("Problem with Objective Function Coefficients\n")
    parts.append(_format_named(x.obj, names))
    if x.solved == 1:
        parts.append("\n\nOptimal solution has the following values\n")
        parts.append(_format_named(x.soln, names))
        parts.append(
            "The optimal value of the objective  function is "
            + _r_character(float(x.value))
            + ".\n"
        )
    elif x.solved == 0:
        parts.append("\n\nIteration limit exceeded without finding solution\n")
        parts.append("The coefficient values at termination were\n")
        parts.append(_format_named(x.soln, names))
        parts.append(
            "The objective function value was " + _r_character(float(x.value)) + ".\n"
        )
    else:
        parts.append("\nNo feasible solution could be found\n")
    text = "".join(parts)
    print(text, end="")
    return text


def _simplex1(a, A, b, basic, val, stage, n1, eps, n_iter):
    if A is None:
        raise ValueError("simplex has no constraint matrix")
    A = np.asarray(A, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    N = int(A.shape[1])
    M = int(A.shape[0])
    basic = [int(v) for v in basic]
    if any(v < 1 or v > N for v in basic):
        raise IndexError("subscript out of bounds")
    chosen = set(basic)
    nonbasic = [i for i in range(1, N + 1) if i not in chosen]
    nb0 = [i - 1 for i in nonbasic]
    tableau = np.column_stack([b, -A[:, nb0]])
    if stage == 2:
        tableau = np.vstack([tableau, np.concatenate([[val], a[nb0]])])
        obfun = a[nb0].copy()
    else:
        start = M + n1 - N + 1
        obfun_full = tableau[start - 1 : M, :].sum(axis=0)
        tableau = np.vstack(
            [np.concatenate([[val], a[nb0]]), tableau, obfun_full]
        )
        obfun = obfun_full[1:].copy()

    it = 1
    temp = None
    while (not bool(np.all(obfun > -eps))) and it <= n_iter:
        pcol = int(np.argmin(obfun)) + 2
        if stage == 2:
            column = tableau[0:M, pcol - 1]
            neg = [i + 1 for i in range(M) if column[i] < -eps]
        else:
            column = tableau[1 : M + 1, pcol - 1]
            neg = [i + 2 for i in range(M) if column[i] < -eps]
        if not neg:
            raise ValueError("simplex pivot failed: no eligible row")
        ratios = np.array(
            [-tableau[row - 1, 0] / tableau[row - 1, pcol - 1] for row in neg]
        )
        prow = neg[int(np.argmin(ratios))]
        _pivot(tableau, prow, pcol)
        if stage == 1:
            temp = basic[prow - 2]
            basic[prow - 2] = nonbasic[pcol - 2]
            nonbasic[pcol - 2] = temp
            obfun = tableau[M + 1, 1:].copy()
        else:
            temp = basic[prow - 1]
            basic[prow - 1] = nonbasic[pcol - 2]
            nonbasic[pcol - 2] = temp
            obfun = tableau[M, 1:].copy()
        it += 1

    if stage == 1:
        val_aux = float(tableau[M + 1, 0])
        if val_aux < eps and any(v > n1 for v in basic):
            if temp is None:
                raise NameError("object 'temp' not found")
            artificial_rows = [i + 1 for i, v in enumerate(basic) if v > n1]
            # seq_along(temp) is 1: temp is the last swapped scalar.
            for j in range(1):
                prow = 1 + artificial_rows[j]
                subset = [
                    nonbasic[k]
                    for k in range(len(nonbasic))
                    if abs(tableau[prow - 1, k + 1]) > eps
                ]
                if not subset:
                    raise ValueError("simplex pivot failed: no eligible column")
                pcol = int(np.argmin(np.asarray(subset, dtype=float))) + 2
                _pivot(tableau, prow, pcol)
                swapped = basic[prow - 2]
                basic[prow - 2] = nonbasic[pcol - 2]
                nonbasic[pcol - 2] = swapped
        soln = np.zeros(N, dtype=np.float64)
        for i, variable in enumerate(basic):
            soln[variable - 1] = tableau[i + 1, 0]
        A_out = np.zeros((M, N), dtype=np.float64)
        for i, variable in enumerate(basic):
            A_out[i, variable - 1] = 1.0
        block = -tableau[1 : M + 1, 1:]
        for j, variable in enumerate(nonbasic):
            A_out[:, variable - 1] = block[:, j]
        a_orig = np.zeros(N, dtype=np.float64)
        a_aux = np.zeros(N, dtype=np.float64)
        for j, variable in enumerate(nonbasic):
            a_orig[variable - 1] = tableau[0, j + 1]
            a_aux[variable - 1] = tableau[M + 1, j + 1]
        return {
            "soln": soln,
            "solved": -1,
            "value": float(tableau[0, 0]),
            "val_aux": val_aux,
            "A": A_out,
            "a": a_orig,
            "a_aux": a_aux,
            "basic": basic,
        }

    soln = np.zeros(N, dtype=np.float64)
    for i, variable in enumerate(basic):
        soln[variable - 1] = tableau[i, 0]
    A_out = np.zeros((M, N), dtype=np.float64)
    for i, variable in enumerate(basic):
        A_out[i, variable - 1] = 1.0
    block = tableau[0:M, 1:]
    for j, variable in enumerate(nonbasic):
        A_out[:, variable - 1] = block[:, j]
    a_out = np.zeros(N, dtype=np.float64)
    for j, variable in enumerate(nonbasic):
        a_out[variable - 1] = tableau[M, j + 1]
    solved = 1 if it <= n_iter else 0
    return {
        "soln": soln,
        "solved": solved,
        "value": float(tableau[M, 0]),
        "A": A_out,
        "a": a_out,
        "basic": basic,
    }


def _pivot(tab, pr, pc):
    pr0 = pr - 1
    pc0 = pc - 1
    pv = tab[pr0, pc0]
    pcv = tab[:, pc0].copy()
    other = np.ones(tab.shape[0], dtype=bool)
    other[pr0] = False
    coeff = tab[other, pc0] / pv
    tab[other, :] = tab[other, :] - coeff[:, None] * tab[pr0, :]
    tab[pr0, :] = tab[pr0, :] / (-pv)
    tab[pr0, pc0] = 1.0 / pv
    tab[other, pc0] = pcv[other] / pv


def _as_rows(A, n, name):
    if A is None:
        return None, 0
    arr = np.asarray(A, dtype=np.float64)
    if arr.ndim == 0:
        arr = arr.reshape(1, 1)
    elif arr.ndim == 1:
        arr = arr.reshape(1, -1)
    elif arr.ndim != 2:
        raise ValueError(f"{name} must be a vector or a matrix")
    if arr.shape[1] != n:
        raise ValueError(f"{name} has {arr.shape[1]} columns and a has length {n}")
    return arr, int(arr.shape[0])


def _as_rhs(b, m, name):
    if m == 0:
        return np.zeros(0, dtype=np.float64)
    if b is None:
        raise ValueError(f"{name} is required")
    arr = np.asarray(b, dtype=np.float64).reshape(-1)
    if arr.shape[0] != m:
        raise ValueError(f"{name} has length {arr.shape[0]} and the constraint has {m} rows")
    return arr


def _as_rhs_cat(parts):
    kept = [vector for vector, m in parts if m > 0]
    if not kept:
        return np.zeros(0, dtype=np.float64)
    return np.concatenate(kept)


def _iden(n):
    if n > 0:
        return np.eye(n, dtype=np.float64)
    return None


def _zero(n, m):
    if n > 0 and m > 0:
        return np.zeros((n, m), dtype=np.float64)
    return None


def _rbind(*parts):
    rows = []
    for part in parts:
        if part is None:
            continue
        arr = np.asarray(part, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        rows.append(arr)
    if not rows:
        return None
    return np.vstack(rows)


def _cbind(*parts):
    cols = []
    for part in parts:
        if part is None:
            continue
        arr = np.asarray(part, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        cols.append(arr)
    if not cols:
        return None
    return np.hstack(cols)


def _call_text(a, A1, b1, A2, b2, A3, b3, maxi, n_iter, eps, default_iter):
    pieces = [f"a={_fmt_arg(a)}"]
    if A1 is not None:
        pieces.append(f"A1={_fmt_arg(A1)}")
    if b1 is not None:
        pieces.append(f"b1={_fmt_arg(b1)}")
    if A2 is not None:
        pieces.append(f"A2={_fmt_arg(A2)}")
    if b2 is not None:
        pieces.append(f"b2={_fmt_arg(b2)}")
    if A3 is not None:
        pieces.append(f"A3={_fmt_arg(A3)}")
    if b3 is not None:
        pieces.append(f"b3={_fmt_arg(b3)}")
    if maxi:
        pieces.append("maxi=True")
    if n_iter != default_iter:
        pieces.append(f"n_iter={n_iter}")
    if eps != 1e-10:
        pieces.append(f"eps={_r_character(float(eps))}")
    return "simplex(" + ", ".join(pieces) + ")"


def _fmt_arg(value):
    if isinstance(value, (bool, np.bool_)):
        return "True" if value else "False"
    arr = np.asarray(value)
    if arr.ndim == 0:
        if isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_)):
            return str(int(value))
        return _r_character(float(arr))
    if arr.ndim == 1:
        return "[" + ", ".join(_fmt_scalar(item) for item in arr) + "]"
    rows = [
        "[" + ", ".join(_fmt_scalar(item) for item in row) + "]" for row in arr
    ]
    return "[" + ", ".join(rows) + "]"


def _fmt_scalar(value):
    number = float(value)
    if number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    return _r_character(number)


def _r_character(value: float) -> str:
    """R as.character for a double: 15 significant digits, shorter scientific form."""

    if math.isnan(value):
        return "NaN"
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
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def _format_named(values, names) -> str:
    formatted = _r_format(np.asarray(values, dtype=np.float64))
    base = max((len(text) for text in formatted), default=0)
    padded = [text.rjust(base) for text in formatted]
    widths = [max(base, len(name)) for name in names]
    name_fields = [name.rjust(width) for name, width in zip(names, widths)]
    value_fields = [text.rjust(width) for text, width in zip(padded, widths)]
    # print.default ends each line with the column gap, a trailing space.
    lines = _wrap(name_fields) + _wrap(value_fields)
    return "".join(line + " \n" for line in lines)


def _wrap(fields, width=_WIDTH):
    lines = []
    current = ""
    for field in fields:
        if not current:
            current = field
            continue
        if len(current) + 1 + len(field) > width:
            lines.append(current)
            current = field
        else:
            current = current + " " + field
    if current:
        lines.append(current)
    return lines


def _r_format(values: np.ndarray) -> list[str]:
    numbers = [float(value) for value in np.asarray(values, dtype=np.float64).reshape(-1)]
    decimals = max((_fixed_decimals(value) for value in numbers), default=0)
    fixed = [_format_fixed(value, decimals) for value in numbers]
    mantissa_decimals = max((_sci_mantissa_decimals(value) for value in numbers), default=0)
    scientific = [_format_sci(value, mantissa_decimals) for value in numbers]
    fixed_width = max((len(text) for text in fixed), default=0)
    sci_width = max((len(text) for text in scientific), default=0)
    if fixed_width > sci_width + _SCIPEN:
        return scientific
    return fixed


def _sig_text(value: float) -> tuple[str, int]:
    text = format(abs(value), f".{_DIGITS - 1}e")
    mantissa, exponent_text = text.split("e")
    return mantissa, int(exponent_text)


def _fixed_decimals(value: float) -> int:
    if value == 0.0 or not math.isfinite(value):
        return 0
    mantissa, exponent = _sig_text(value)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    after = len(whole + frac) - (exponent + 1)
    return max(after, 0)


def _sci_mantissa_decimals(value: float) -> int:
    if value == 0.0 or not math.isfinite(value):
        return 0
    mantissa, _exponent = _sig_text(value)
    _whole, frac = mantissa.split(".")
    return len(frac.rstrip("0"))


def _format_fixed(value: float, decimals: int) -> str:
    if decimals == 0:
        return str(int(round(value)))
    return f"{value:.{decimals}f}"


def _format_sci(value: float, mantissa_decimals: int) -> str:
    negative = value < 0
    magnitude = abs(value)
    if magnitude == 0.0:
        body = "0" if mantissa_decimals == 0 else "0." + ("0" * mantissa_decimals)
        exponent = 0
    else:
        raw = f"{magnitude:.{mantissa_decimals}e}"
        body, exponent_text = raw.split("e")
        exponent = int(exponent_text)
    text = f"{body}e{exponent:+03d}"
    if negative:
        text = "-" + text
    return text
