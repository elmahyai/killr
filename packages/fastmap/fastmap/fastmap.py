"""A string-keyed map that does not use the R symbol table.

Translated from fastmap 1.2.0 ``fastmap`` in ``R/fastmap.R``. The
string-to-index lookup is the Rust port of ``src/fastmap.cpp``. Values
and the free-slot stack stay here, so ``keys()`` follows the same hole
order as R.
"""

from __future__ import annotations

import math

from fastmap_kernel import IndexMap

_MISSING = object()
_INITIAL_SIZE = 32
_GROWTH_FACTOR = 1.2
_SHRINK_FACTOR = 2

_KEY_TYPE = "key must be a one-element character vector"
_KEY_BLANK = 'key must be not be "" or NA'
_MSET_NAMES = "mset: all values must be named."
_MGET_TYPE = "mget: `keys` must be a character vector or NULL"
_REMOVE_TYPE = "remove: `keys` must be a character vector or NULL"
_REMOVE_BLANK = 'remove: `keys` must not be "" or NA'


def fastmap(missing_default=None):
    """Return a map from strings to arbitrary objects.

    ``get`` of an unknown key returns ``missing_default`` (``None`` unless
    you pass another sentinel). Keys are Unicode strings: two R strings
    that differ only by encoding are one key here.
    """
    return FastMap(missing_default)


class NamedList(list):
    """A list with a parallel ``names`` vector. Duplicate names are kept."""

    def __init__(self, pairs=()):
        pairs = list(pairs)
        super().__init__(value for _, value in pairs)
        self.names = [name for name, _ in pairs]

    def __eq__(self, other):
        if not isinstance(other, NamedList):
            return False
        return self.names == other.names and list(self) == list(other)

    def __repr__(self):
        if len(self) == 0:
            return "named list()"
        body = ", ".join(
            f"{name}={value!r}" for name, value in zip(self.names, self)
        )
        return f"named list({body})"


class FastMap:
    def __init__(self, missing_default=None):
        self.missing_default = missing_default
        self.reset()

    def reset(self):
        """Drop every entry."""
        self._n = 0
        self._index = IndexMap()
        self._keys = [None] * _INITIAL_SIZE
        self._values = [None] * _INITIAL_SIZE
        self._holes = list(range(_INITIAL_SIZE))
        self._n_holes = _INITIAL_SIZE
        return None

    def set(self, key, value):
        """Store ``value`` under ``key`` and return ``value``.

        A new key takes the last free hole, so the first keys sit at the
        end of the initial buffer. ``None`` is a stored value.
        """
        text = _one_key(key)
        idx = self._index.get(text)
        if idx == -1:
            self._n += 1
            if self._n_holes == 0:
                self._grow()
            idx = self._holes[self._n_holes - 1]
            self._holes[self._n_holes - 1] = None
            self._n_holes -= 1
            self._index.set(text, idx)
        self._values[idx] = value
        self._keys[idx] = text
        return value

    def mset(self, *args, _list=None, **kwargs):
        """Store several named values. Names are checked before any write.

        Keyword arguments are stored first, then ``_list`` (R's ``.list``).
        An empty call returns an empty named list.
        """
        if args:
            raise ValueError(_MSET_NAMES)
        pairs = list(kwargs.items())
        if _list is None:
            extra = []
        elif isinstance(_list, dict):
            extra = list(_list.items())
        elif isinstance(_list, NamedList):
            extra = list(zip(_list.names, _list))
        elif isinstance(_list, (list, tuple)):
            if len(_list) == 0:
                extra = []
            else:
                raise ValueError(_MSET_NAMES)
        else:
            raise ValueError(_MSET_NAMES)
        pairs.extend(extra)
        if len(pairs) == 0:
            return NamedList([])
        for name, _value in pairs:
            if name is None or name == "" or not isinstance(name, str):
                raise ValueError(_MSET_NAMES)
        for name, value in pairs:
            self.set(name, value)
        return NamedList(pairs)

    def get(self, key, missing=_MISSING):
        """Return the value for ``key``, or ``missing`` when it is absent."""
        if missing is _MISSING:
            missing = self.missing_default
        text = _one_key(key)
        idx = self._index.get(text)
        if idx == -1:
            return missing
        return self._values[idx]

    def mget(self, keys, missing=_MISSING):
        """Return values for ``keys``, in that order, with duplicate names kept."""
        if missing is _MISSING:
            missing = self.missing_default
        if keys is None:
            return NamedList([])
        vector = _character_vector(keys, _MGET_TYPE)
        return NamedList((key, self.get(key, missing)) for key in vector)

    def has(self, keys):
        """Return whether each key is present.

        One key returns a bool. Several keys return a list of bools.
        ``None`` and an empty list return an empty list.
        """
        if keys is None:
            return []
        vector = _character_vector(keys, _MGET_TYPE)
        if len(vector) == 1:
            return self._has_one(vector[0])
        return [self._has_one(key) for key in vector]

    def remove(self, keys):
        """Remove each key. Return whether it was present.

        One key returns a bool. Blank and missing keys raise before any
        removal. A repeated key is true the first time and false after that.
        """
        if keys is None:
            return []
        vector = _character_vector(keys, _REMOVE_TYPE)
        for key in vector:
            if key is None or key == "" or not isinstance(key, str):
                raise ValueError(_REMOVE_BLANK)
        if len(vector) == 1:
            return self._remove_one(vector[0])
        return [self._remove_one(key) for key in vector]

    def size(self):
        """Return how many keys are stored."""
        return self._n

    def keys(self, sort=False):
        """Return the keys.

        The default order is ascending slot order, which is the reverse of
        insertion while the first buffer is filling. ``sort=True`` orders
        by Unicode code point.
        """
        found = [self._keys[index] for index in self._occupied()]
        if sort:
            found = sorted(found)
        return found

    def clone(self):
        """Return a shallow copy. Later writes do not cross the copy."""
        other = FastMap(self.missing_default)
        other._n = self._n
        other._index = self._index.copy()
        other._keys = list(self._keys)
        other._values = list(self._values)
        other._holes = list(self._holes)
        other._n_holes = self._n_holes
        return other

    def as_list(self, sort=False):
        """Return a named list of every entry, in ``keys()`` order."""
        indexes = self._occupied()
        pairs = [(self._keys[index], self._values[index]) for index in indexes]
        if sort:
            pairs = sorted(pairs, key=lambda pair: pair[0])
        return NamedList(pairs)

    def _has_one(self, key):
        text = _one_key(key)
        return self._index.has(text)

    def _remove_one(self, key):
        text = _one_key(key)
        idx = self._index.remove(text)
        if idx == -1:
            return False
        self._values[idx] = None
        self._keys[idx] = None
        self._n -= 1
        self._n_holes += 1
        if len(self._holes) < self._n_holes:
            self._holes.extend([None] * (self._n_holes - len(self._holes)))
        self._holes[self._n_holes - 1] = idx
        length = len(self._values)
        if length > _INITIAL_SIZE and length >= self._n * _SHRINK_FACTOR:
            self._shrink()
        return True

    def _occupied(self):
        if self._n_holes == 0:
            return list(range(len(self._keys)))
        holes = set(self._holes[: self._n_holes])
        return [index for index in range(len(self._keys)) if index not in holes]

    def _grow(self):
        old = len(self._values)
        new = int(math.ceil(old * _GROWTH_FACTOR))
        extra = new - old
        self._values.extend([None] * extra)
        self._keys.extend([None] * extra)
        if len(self._holes) < new:
            self._holes.extend([None] * (new - len(self._holes)))
        self._n_holes = extra
        for offset, slot in enumerate(range(old, new)):
            self._holes[offset] = slot

    def _shrink(self):
        if self._n_holes == 0:
            return None
        pairs = self._index.keys_idxs(False)
        holes = self._holes[: self._n_holes]
        hole_set = set(holes)
        remap_inv = [
            index for index in range(len(self._values)) if index not in hole_set
        ]
        if len(pairs) != len(remap_inv):
            raise RuntimeError("length mismatch of keys_idxs and remap_inv")
        remap = [0] * len(self._values)
        for new_index, old_index in enumerate(remap_inv):
            remap[old_index] = new_index
        for key, idx in pairs:
            self._index.set(key, remap[idx])
        self._values = [self._values[index] for index in remap_inv]
        self._keys = [self._keys[index] for index in remap_inv]
        self._holes = []
        self._n_holes = 0
        self._n = len(self._values)
        return None


def _one_key(key):
    if isinstance(key, str):
        text = key
    elif isinstance(key, (list, tuple)) and len(key) == 1 and isinstance(key[0], str):
        text = key[0]
    elif (
        isinstance(key, (list, tuple))
        and len(key) == 1
        and key[0] is None
    ):
        raise ValueError(_KEY_BLANK)
    else:
        raise ValueError(_KEY_TYPE)
    if text == "":
        raise ValueError(_KEY_BLANK)
    return text


def _character_vector(keys, message):
    if isinstance(keys, str):
        return [keys]
    if isinstance(keys, (list, tuple)):
        return list(keys)
    raise ValueError(message)
