"""A stack of arbitrary objects.

Translated from fastmap 1.2.0 ``faststack`` in ``R/faststack.R``.
The backing store is a Python list. No C kernel is involved.
"""

from __future__ import annotations

from fastmap.fastqueue import _as_integer, _collect, _length

_MISSING = object()


def faststack(init=20, missing_default=None):
    """Return a stack.

    ``push`` and ``mpush`` add on top. ``pop`` and ``mpop`` take from the
    top. ``as_list`` runs from the bottom to the top. ``init`` is the
    starting capacity and the smallest ``mpop`` shrinks to. An empty
    ``pop`` or ``peek`` returns ``missing_default``.
    """
    return FastStack(init, missing_default)


class FastStack:
    def __init__(self, init=20, missing_default=None):
        self.init = _length(init)
        self.missing_default = missing_default
        self._s = [None] * self.init
        self.count = 0

    def push(self, x):
        """Push one object. ``None`` is stored, not skipped."""
        new_size = self.count + 1
        if new_size > len(self._s):
            self._s.append(x)
        else:
            self._s[new_size - 1] = x
        self.count = new_size
        return None

    def mpush(self, *args, _list=None):
        """Push several objects, last argument on top.

        ``_list`` is R's ``.list`` and is pushed after the positional
        objects. An empty call raises ``ValueError``.
        """
        items = _collect(args, _list)
        if len(items) == 0:
            raise ValueError("`mpush`: No items provided to push on stack.")
        new_size = self.count + len(items)
        if new_size > len(self._s):
            self._s.extend([None] * (new_size - len(self._s)))
        for offset, item in enumerate(items):
            self._s[self.count + offset] = item
        self.count = new_size
        return None

    def pop(self, missing=_MISSING):
        """Pop the top object. An empty stack returns ``missing``."""
        if missing is _MISSING:
            missing = self.missing_default
        if self.count == 0:
            return missing
        value = self._s[self.count - 1]
        self._s[self.count - 1] = None
        self.count -= 1
        length = len(self._s)
        if length > self.init and self.count < length / 2:
            new_len = max(self.init, self.count)
            for index in range(new_len, length):
                self._s[index] = None
        return value

    def mpop(self, n, missing=_MISSING):
        """Pop the top ``n`` objects. The first element is the old top.

        Slots past the end of the stack are ``missing``. ``None`` leaves
        those slots as ``None``.
        """
        if missing is _MISSING:
            missing = self.missing_default
        n = _as_integer(n)
        if n < 1:
            raise ValueError("`n` must be at least 1.")
        if n > self.count:
            n_pop = self.count
            n_extra = n - self.count
        else:
            n_pop = n
            n_extra = 0
        if n_pop == 0:
            idx = []
        else:
            idx = list(range(self.count - 1, self.count - n_pop - 1, -1))
        values = [None] * n
        for offset, index in enumerate(idx):
            values[offset] = self._s[index]
        if n_extra != 0 and missing is not None:
            for offset in range(n_pop, n):
                values[offset] = missing
        for index in idx:
            self._s[index] = None
        self.count -= n_pop
        length = len(self._s)
        if length > self.init and self.count < length / 2:
            new_len = max(self.init, self.count)
            del self._s[new_len:]
        return values

    def peek(self, missing=_MISSING):
        """Return the top object without removing it."""
        if missing is _MISSING:
            missing = self.missing_default
        if self.count == 0:
            return missing
        return self._s[self.count - 1]

    def reset(self):
        """Drop every object and restore the starting capacity."""
        self._s = [None] * self.init
        self.count = 0
        return None

    def size(self):
        """Return how many objects are on the stack."""
        return self.count

    def as_list(self):
        """Return the objects from bottom to top."""
        return self._s[: self.count]
