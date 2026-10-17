"""Shortest edit script.

The edit list comes from the ``myersmba`` crate, a port of ``src/diff.c``.
Offsets there are 0-based. This module adds one, which is what ``diff_myers``
does after ``.Call``, and formats the GNU commands the way ``as.character``
does for a ``MyersMbaSes`` object.

``NA`` is replaced by the string ``"NA"`` only for the comparison. ``ses_dat``
reads the original value, so a missing element stays missing.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence

from myersmba import myers_diff

from diffobj.options import gdo

_KINDS = ("Match", "Insert", "Delete")
_ORDER = {"Match": 1, "Insert": 3, "Delete": 2}
_INT_MIN = -2147483647
_INT_MAX = 2147483647


class MyersMbaSes:
    """Grouped edit script. ``kind`` uses the R factor levels."""

    def __init__(self, a: list[str], b: list[str], kind: list[str], length: list[int], offset: list[int], diffs: int):
        self.a = a
        self.b = b
        self.kind = kind
        self.length = length
        self.offset = offset
        self.diffs = diffs


def _r_character_double(value: float) -> str:
    """R ``as.character`` for a double that is not missing."""

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


def _one_character(value, argument: str):
    """One element of ``as.character``. ``None`` stays missing."""

    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _r_character_double(value)
    raise TypeError(
        f"Argument `{argument}` is not character and could not be coerced to such"
    )


def _as_character(value, argument: str) -> list:
    """``as.character`` of a scalar or an atomic vector. Missing elements stay ``None``."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, (bool, int, float)):
        return [_one_character(value, argument)]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [_one_character(item, argument) for item in value]
    raise TypeError(
        f"Argument `{argument}` is not character and could not be coerced to such"
    )


def _is_true_false(value) -> bool:
    return isinstance(value, bool)


def _scalar_integer(value, name: str) -> int:
    """``as.integer`` of a length-1 number, then ``is.int.1L``."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Argument `{name}` must be scalar integer.")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Argument `{name}` must be scalar integer.")
        value = math.trunc(value)
    if value < _INT_MIN or value > _INT_MAX:
        raise ValueError(f"Argument `{name}` must be scalar integer.")
    return int(value)


def _prepare(value, argument: str) -> tuple[list, list[str]]:
    original = _as_character(value, argument)
    compared = ["NA" if item is None else item for item in original]
    return original, compared


def diff_myers(a: Sequence[str], b: Sequence[str], max_diffs: int = -1, warn: bool = False) -> MyersMbaSes:
    """Grouped Myers script. ``a`` and ``b`` must already be character, with no missing values."""

    if any(item is None for item in a) or any(item is None for item in b):
        raise ValueError("all(!is.na(c(a, b))) is not TRUE")
    max_diffs = _scalar_integer(max_diffs, "max.diffs")
    if not _is_true_false(warn):
        raise ValueError("Argument `warn` must be TRUE or FALSE.")
    kind_code, length, offset, diffs = myers_diff(list(a), list(b), max_diffs)
    kind = [_KINDS[code - 1] for code in kind_code]
    offset = [item + 1 for item in offset]
    if warn and diffs < 0:
        warnings.warn(
            f"Exceeded `max.diffs`: {abs(diffs)} vs {max_diffs} allowed. "
            "Diff is probably suboptimal.",
            stacklevel=2,
        )
    return MyersMbaSes(list(a), list(b), kind, list(length), offset, int(diffs))


def _frame(script: MyersMbaSes) -> list[dict]:
    """The columns ``as.data.frame`` adds before the match rows are dropped."""

    kind = script.kind
    length = script.length
    offset = script.offset
    n = len(kind)
    if n == 0:
        return []
    matches = [item == "Match" for item in kind]
    section = []
    acc = 0
    previous = False
    for flag in matches:
        acc += int(flag) + int(previous)
        section.append(acc)
        previous = flag
    running = None
    cummax = []
    for item, off, size in zip(kind, offset, length):
        val = 1 if item == "Insert" else off + size
        running = val if running is None else max(running, val)
        cummax.append(running)
    last_a = [0] + [cummax[i] - 1 for i in range(n - 1)]
    total = 0
    summed = []
    for item, size in zip(kind, length):
        total += 0 if item == "Delete" else size
        summed.append(total)
    last_b = [0] + summed[:-1]
    rows = []
    for i in range(n):
        rows.append(
            {
                "type": kind[i],
                "len": length[i],
                "off": offset[i],
                "section": section[i],
                "last.a": last_a[i],
                "last.b": last_b[i],
            }
        )
    return rows


def _ses_range(off: int, size: int) -> str:
    if size > 1:
        return f"{off},{off + size - 1}"
    return str(off)


def as_character_ses(script: MyersMbaSes) -> list[str]:
    """GNU edit commands, one string per changed section."""

    rows = [row for row in _frame(script) if row["type"] != "Match"]
    if not rows:
        return []
    groups: list[list[dict]] = []
    current: list[dict] = []
    section = None
    for row in rows:
        if section is None or row["section"] != section:
            if current:
                groups.append(current)
            current = [row]
            section = row["section"]
        else:
            current.append(row)
    if current:
        groups.append(current)
    commands = []
    for group in groups:
        deleted = sum(row["len"] for row in group if row["type"] == "Delete")
        inserted = sum(row["len"] for row in group if row["type"] == "Insert")
        if deleted:
            first = next(row for row in group if row["type"] == "Delete")
            delete_at = first["off"]
        if inserted:
            first = next(row for row in group if row["type"] == "Insert")
            insert_at = first["off"]
        if deleted and inserted:
            commands.append(f"{_ses_range(delete_at, deleted)}c{_ses_range(insert_at, inserted)}")
        elif deleted:
            commands.append(f"{_ses_range(delete_at, deleted)}d{group[0]['last.b']}")
        elif inserted:
            commands.append(f"{group[0]['last.a']}a{_ses_range(insert_at, inserted)}")
        else:
            raise RuntimeError("Logic Error: unexpected edit type; contact maintainer.")
    return commands


def ses(a, b, max_diffs=None, warn=None) -> list[str]:
    """Shortest edit script that turns ``a`` into ``b``."""

    if max_diffs is None:
        max_diffs = gdo("max.diffs")
    if warn is None:
        warn = gdo("warn")
    original_a, compared_a = _prepare(a, "a")
    _original_b, compared_b = _prepare(b, "b")
    max_diffs = _scalar_integer(max_diffs, "max.diffs")
    if not _is_true_false(warn):
        raise ValueError("Argument `warn` must be TRUE or FALSE.")
    del original_a
    script = diff_myers(compared_a, compared_b, max_diffs, warn)
    return as_character_ses(script)


def ses_dat(a, b, extra: bool = True, max_diffs=None, warn=None) -> list[dict]:
    """One row per element, including matches.

    ``op`` is ``Match``, ``Insert``, or ``Delete``. ``val`` is the original
    element, with ``None`` for a missing value. When ``extra`` is true, ``id_a``
    and ``id_b`` are 1-based indexes. A match records only ``id_a``, because
    that is the vector the value was copied from.
    """

    if max_diffs is None:
        max_diffs = gdo("max.diffs")
    if warn is None:
        warn = gdo("warn")
    original_a, compared_a = _prepare(a, "a")
    original_b, compared_b = _prepare(b, "b")
    max_diffs = _scalar_integer(max_diffs, "max.diffs")
    if not _is_true_false(warn):
        raise ValueError("Argument `warn` must be TRUE or FALSE.")
    if not _is_true_false(extra):
        raise ValueError("Argument `extra` must be TRUE or FALSE.")
    script = diff_myers(compared_a, compared_b, max_diffs, warn)
    n = len(script.kind)
    section = []
    acc = 0
    for kind in script.kind:
        acc += kind == "Match"
        section.append(acc)
    order = sorted(range(n), key=lambda i: (section[i], _ORDER[script.kind[i]]))
    rows = []
    for index in order:
        kind = script.kind[index]
        size = script.length[index]
        off = script.offset[index]
        for step in range(size):
            at = off + step
            if kind in ("Match", "Delete"):
                val = original_a[at - 1]
                id_a = at
                id_b = None
            else:
                val = original_b[at - 1]
                id_a = None
                id_b = at
            row = {"op": kind, "val": val}
            if extra:
                row["id_a"] = id_a
                row["id_b"] = id_b
            rows.append(row)
    return rows
