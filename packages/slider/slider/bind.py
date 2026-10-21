"""Bind window results into one frame, as `vctrs::vec_rbind` and `vec_cbind` do.

A data frame is a Polars `DataFrame`. The R `*_dfr()` and `*_dfc()` wrappers run
the ordinary windowed call and hand the list of results to one of these binders.

A result that is a data frame contributes all its columns and rows. Anything
else has no dimensions of its own, so the binder interprets it: row binding
reads a scalar as a one-cell row and a sequence as a one-row record, column
binding reads either as a single column.

A column without a name of its own is `...n` for the nth column, which is also
how vctrs reads a name that already looks like `...n`. Repeats are numbered by
position, `a...1`/`a...2`, so `a, b, a` becomes `a...1`, `b`, `a...3`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import polars as pl

from slider.errors import SliderError

ROW_REPAIR = ("unique", "universal", "check_unique")
COL_REPAIR = ("unique", "universal", "check_unique", "minimal")

_POSITIONAL = re.compile(r"^\.\.\.\d+$")


class _ZapType:
    """`rlang::zap()`: the default that asks `*_dfr()` to drop the source column."""

    def __repr__(self) -> str:
        return "zap()"


ZAP = _ZapType()


def _mode(name_repair, allowed: tuple[str, ...]) -> str:
    if isinstance(name_repair, (list, tuple)):
        if not name_repair:
            raise SliderError("`.name_repair` must not be empty.")
        name_repair = name_repair[0]
    if name_repair not in allowed:
        names = ", ".join(f'"{name}"' for name in allowed)
        raise SliderError(f"`.name_repair` can't be {name_repair!r}. It must be one of {names}.")
    return name_repair


def _universal(name: str) -> str:
    if not name:
        return "..."
    text = "".join(char if (char.isalnum() or char in "._") else "." for char in name)
    if not (text[0].isalpha() or text[0] == "."):
        text = f"..{text}"
    return text


def _is_positional(name: str) -> bool:
    return not name or bool(_POSITIONAL.match(name))


def _positional_names(count: int) -> list[str]:
    return [f"...{index}" for index in range(1, count + 1)]


def _repair(names: list[str], mode: str) -> list[str]:
    """vctrs name repair. `unique` numbers every repeat by its column position."""
    if mode == "minimal":
        return names
    if mode == "universal":
        names = [_universal(name) for name in names]
    if mode == "check_unique":
        if len(set(names)) != len(names):
            raise SliderError("Names must be unique.")
        return names

    counts: dict[str, int] = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    taken: set[str] = set()
    out: list[str] = []
    for position, name in enumerate(names, start=1):
        if counts[name] == 1 and name not in taken:
            taken.add(name)
            out.append(name)
            continue
        suffix = position
        while f"{name}...{suffix}" in taken:
            suffix += 1
        candidate = f"{name}...{suffix}"
        taken.add(candidate)
        out.append(candidate)
    return out


def _is_bare(value) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _mapping_frame(value: Mapping) -> pl.DataFrame:
    """A mapping is a data frame: a sequence is a column, a scalar a one-cell column."""
    columns = {}
    for key, column in value.items():
        columns[str(key)] = list(column) if _is_bare(column) else [column]
    return pl.DataFrame(columns)


def _row_frame(value) -> pl.DataFrame:
    """A result with no rows of its own is one row."""
    if isinstance(value, pl.DataFrame):
        return value
    if isinstance(value, pl.Series):
        return value.to_frame()
    if isinstance(value, Mapping):
        return _mapping_frame(value)
    if _is_bare(value):
        return pl.DataFrame({name: [cell] for name, cell in zip(_positional_names(len(value)), value)})
    return pl.DataFrame({"...1": [value]})


def _col_columns(value) -> list[tuple[str, list]]:
    """A data frame and a mapping contribute their columns; anything else is one column."""
    if isinstance(value, Mapping):
        value = _mapping_frame(value)
    if isinstance(value, pl.DataFrame):
        return [(name, value[name].to_list()) for name in value.columns]
    if isinstance(value, pl.Series):
        return [("", value.to_list())]
    if _is_bare(value):
        return [("", list(value))]
    return [("", [value])]


def vec_rbind(results, names_to=ZAP, name_repair: str = "unique") -> pl.DataFrame:
    """Stack window results by column name, filling an absent cell with a null.

    A null result contributes no row, though it still counts as one window, so
    `.names_to` labels the rest of the results by their original position.
    """
    mode = _mode(name_repair, ROW_REPAIR)
    if not (names_to is ZAP or names_to is None or isinstance(names_to, str)):
        raise SliderError("`.names_to` must be `NULL`, a string, or an `rlang::zap()` object.")

    if isinstance(results, Mapping):
        labels: list = list(results)
        items = [results[label] for label in labels]
    else:
        items = list(results)
        labels = list(range(1, len(items) + 1))

    frames: list[pl.DataFrame] = []
    kept: list = []
    for label, value in zip(labels, items):
        if value is None:
            continue
        frame = _row_frame(value)
        fallback = _positional_names(frame.width)
        names = [fallback[index] if _is_positional(name) else name
                 for index, name in enumerate(frame.columns)]
        frame = frame.rename(dict(zip(frame.columns, _repair(names, mode))))
        frames.append(frame)
        kept.append(label)

    if not frames:
        return pl.DataFrame()

    out = pl.concat(frames, how="diagonal_relaxed")
    if isinstance(names_to, str):
        cells = [label for label, frame in zip(kept, frames) for _ in range(frame.height)]
        out = out.select([pl.Series(names_to, cells), pl.all()])
    return out


def vec_cbind(results, size=None, name_repair: str = "unique") -> pl.DataFrame:
    """Place window results side by side, recycling a result of one row.

    A null result contributes no column. A single-row result is recycled to the
    common height, which is `.size` when given and otherwise the tallest result.
    """
    mode = _mode(name_repair, COL_REPAIR)
    if size is not None:
        if isinstance(size, bool) or not isinstance(size, int):
            raise SliderError("`.size` must be an integer.")
        if size < 0:
            raise SliderError("`.size` must be positive.")

    items = list(results.values()) if isinstance(results, Mapping) else list(results)
    columns: list[tuple[str, list]] = []
    for value in items:
        if value is None:
            continue
        found = _col_columns(value)
        # Positional fallbacks run over the whole result, not each argument, so
        # six unnamed one-column windows become ...1 through ...6.
        offset = len(columns)
        columns.extend(
            ((f"...{offset + index}" if _is_positional(name) else name), cells)
            for index, (name, cells) in enumerate(found, start=1)
        )

    if not columns:
        return pl.DataFrame()

    heights = {len(cells) for _, cells in columns if len(cells) != 1}
    if len(heights) > 1:
        low, high = sorted(heights)
        raise SliderError(f"Can't recycle input of size {low} to size {high}.")
    height = heights.pop() if heights else (size if size is not None else 1)
    if size is not None and size != height:
        raise SliderError(f"Can't recycle input of size {height} to size {size}.")

    names = _repair([name for name, _ in columns], mode)
    data = {}
    for name, (_, cells) in zip(names, columns):
        if name in data:
            raise SliderError(
                f"Can't bind two columns named {name!r}: a Polars frame keeps names "
                "unique, so `.name_repair` needs to be \"unique\" or \"universal\"."
            )
        data[name] = cells * height if len(cells) == 1 else list(cells)
    return pl.DataFrame(data)
