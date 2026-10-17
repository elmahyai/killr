"""Values that carry an R class through toJSON and fromJSON."""

from __future__ import annotations

from dataclasses import dataclass, field


class NAType:
    def __repr__(self) -> str:
        return "NA"

    def __bool__(self) -> bool:
        return False


NA = NAType()


def is_missing(value: object) -> bool:
    return value is NA or value is None and False


class I:
    """Digits wrapped the way R's I() marks significant digits."""

    def __init__(self, value: int):
        self.value = value


@dataclass
class Scalar:
    value: object


@dataclass
class DataFrame:
    columns: dict[str, list] = field(default_factory=dict)

    def __len__(self) -> int:
        if not self.columns:
            return 0
        return len(next(iter(self.columns.values())))

    def column(self, name: str) -> list:
        return self.columns[name]
