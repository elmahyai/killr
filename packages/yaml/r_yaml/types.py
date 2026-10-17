"""R values that Python's own types do not distinguish."""


class NA:
    """One of R's four missing values."""

    def __init__(self, kind):
        self.kind = kind

    def __repr__(self):
        return f"NA_{self.kind}"

    def __eq__(self, other):
        return isinstance(other, NA) and self.kind == other.kind

    def __hash__(self):
        return hash(("NA", self.kind))


NA_LOGICAL = NA("logical")
NA_INTEGER = NA("integer")
NA_REAL = NA("real")
NA_CHARACTER = NA("character")


class Vector(list):
    """An R atomic vector. A one-element vector emits as a scalar."""

    def __init__(self, values, kind, tag=None, classes=(), quoted=False):
        super().__init__(values)
        self.kind = kind
        self.tag = tag
        self.classes = tuple(classes)
        self.quoted = quoted


class DataFrame:
    """Column-oriented frame. column_major emits a map of sequences."""

    def __init__(self, columns, tag=None, classes=("data.frame",)):
        self.columns = dict(columns)
        self.tag = tag
        self.classes = tuple(classes)


class Record:
    """A map whose keys were not coerced to strings."""

    def __init__(self, pairs):
        self.pairs = list(pairs)

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, index):
        return self.pairs[index][1]

    @property
    def keys(self):
        return [key for key, _value in self.pairs]


class Quoted(str):
    """A character scalar with R's quoted attribute."""

    quoted = True

    def __new__(cls, value):
        return str.__new__(cls, value)


class Verbatim(list):
    """Character values emitted without added quotes."""

    classes = ("verbatim",)


class BadAnchor(str):
    """The stand-in R uses for an unknown alias."""

    def __new__(cls, _value="_yaml.bad-anchor_"):
        return str.__new__(cls, "_yaml.bad-anchor_")


class MergeKey:
    """The `<<` key. It is not stored; it merges the value."""


def kind_of(value):
    if isinstance(value, NA):
        return value.kind
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "real"
    if isinstance(value, str):
        return "character"
    return None
