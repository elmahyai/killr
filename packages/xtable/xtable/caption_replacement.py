"""caption<- from xtable 1.8-8 (``caption<-.xtable``).

Sets the ``caption`` attribute on an ``xtable`` object. The replacement
value must have R ``length`` 1 or 2, or be empty.
"""

from __future__ import annotations

from xtable.sanitize import NA


class Xtable:
    """Minimal ``xtable`` object for attribute setters."""

    def __init__(
        self,
        data,
        attrs=None,
        *,
        classes=None,
        col_names=None,
        row_names=None,
    ):
        self.data = data
        self.attrs = {} if attrs is None else dict(attrs)
        self.classes = ("xtable", "data.frame") if classes is None else tuple(classes)
        self.col_names = col_names
        self.row_names = row_names

    def colnames(self) -> list[str]:
        if self.col_names:
            return list(self.col_names)
        return [f"V{i + 1}" for i in range(self.ncol)]

    def rownames(self) -> list[str]:
        if self.row_names is not None:
            return [str(v) for v in self.row_names]
        return [str(i + 1) for i in range(self.nrow)]

    def column(self, index: int) -> list[object]:
        j = index - 1
        return [row[j] for row in self.data]

    @property
    def nrow(self) -> int:
        if not self.data:
            return 0
        return len(self.data)

    @property
    def ncol(self) -> int:
        if not self.data:
            return 0
        row = self.data[0]
        return len(row) if isinstance(row, (list, tuple)) else 1


def _r_length(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _store_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def caption_replacement(x: object, value: object) -> Xtable:
    if not isinstance(x, Xtable):
        raise ValueError(
            f"no applicable method for 'caption<-' applied to an object of class "
            f'"{type(x).__name__}"'
        )
    if _r_length(value) > 2:
        raise ValueError('"caption" must have length 1 or 2')
    x.attrs["caption"] = _store_value(value)
    return x


def caption_attr(x: Xtable) -> object:
    """Same as R ``attr(x, \"caption\", exact = TRUE)`` for checks."""
    if "caption" not in x.attrs:
        return None
    return x.attrs["caption"]
