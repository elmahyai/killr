"""R values that toJSON and fromJSON keep distinct."""

from __future__ import annotations


class NAType:
    """R's logical NA, used as fromJSON's nullValue = NA."""

    def __repr__(self) -> str:
        return "NA"

    def __bool__(self) -> bool:
        raise ValueError("NA is not true or false")


NA = NAType()


class Atomic:
    """An R atomic vector. Missing values are None."""

    def __init__(self, kind: str, values, names=None):
        self.kind = kind
        self.values = list(values)
        self.names = None if names is None else list(names)

    def __len__(self) -> int:
        return len(self.values)

    def __repr__(self) -> str:
        return f"Atomic({self.kind!r}, {self.values!r}, names={self.names!r})"


class RList:
    """An R list. names is None when the list is unnamed, and [] for {}."""

    def __init__(self, values, names=None):
        self.values = list(values)
        self.names = None if names is None else list(names)

    def __len__(self) -> int:
        return len(self.values)

    def __repr__(self) -> str:
        return f"RList({self.values!r}, names={self.names!r})"


class AsIs:
    """The class I() puts on a value so it stays a JSON container."""

    def __init__(self, value):
        self.value = value

    def __repr__(self) -> str:
        return f"AsIs({self.value!r})"


class Matrix:
    """Column-major matrix, the order R stores."""

    def __init__(self, data, nrow: int, ncol: int, kind: str = "integer", names=None):
        self.data = list(data)
        self.nrow = int(nrow)
        self.ncol = int(ncol)
        self.kind = kind
        self.names = None if names is None else list(names)

    def __len__(self) -> int:
        return self.nrow * self.ncol

    def row(self, index: int) -> Atomic:
        values = [self.data[index + self.nrow * column] for column in range(self.ncol)]
        return Atomic(self.kind, values)

    def __repr__(self) -> str:
        return f"Matrix({self.nrow}x{self.ncol}, {self.kind}, {self.data!r})"


class Array:
    """Column-major array. dim is the R dim, first index fastest."""

    def __init__(self, data, dim, kind: str = "integer"):
        self.data = list(data)
        self.dim = tuple(int(item) for item in dim)
        self.kind = kind

    def __repr__(self) -> str:
        return f"Array({self.dim}, {self.kind}, {self.data!r})"


class DataFrame:
    """Columns in order. Each column is an atomic vector or another value."""

    def __init__(self, columns: dict):
        self.columns = dict(columns)

    def __repr__(self) -> str:
        return f"DataFrame({self.columns!r})"


class Factor:
    def __init__(self, labels, names=None):
        self.labels = list(labels)
        self.names = None if names is None else list(names)

    def __len__(self) -> int:
        return len(self.labels)


class Environment:
    """A stand-in for as.list of an environment: a name-to-value mapping."""

    def __init__(self, bindings: dict):
        self.bindings = dict(bindings)


class HexMode:
    def __init__(self, values, names=None):
        self.values = list(values)
        self.names = None if names is None else list(names)

    def __len__(self) -> int:
        return len(self.values)


emptyNamedList = RList([], names=[])
