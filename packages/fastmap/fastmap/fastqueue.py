"""A circular queue of arbitrary objects.

Translated from fastmap 1.2.0 ``fastqueue`` in ``R/fastqueue.R``.
The backing store is a Python list. No C kernel is involved.
"""

from __future__ import annotations

import math

_MISSING = object()


def fastqueue(init=20, missing_default=None):
    """Return a queue.

    ``add`` and ``madd`` append. ``remove`` and ``mremove`` take from the
    front. ``init`` is the starting capacity and the smallest the list
    shrinks to. An empty ``remove`` or ``peek`` returns ``missing_default``.
    """
    return FastQueue(init, missing_default)


class FastQueue:
    def __init__(self, init=20, missing_default=None):
        self.init = _length(init)
        self.missing_default = missing_default
        self._q = [None] * self.init
        self.head = 0
        self.tail = 0
        self.count = 0

    def add(self, x):
        """Append one object. ``None`` is stored, not skipped."""
        capacity = len(self._q)
        if self.count + 1 > capacity:
            capacity = self._resize_at_least(self.count + 1)
        if capacity - self.head >= 1:
            self.head += 1
        else:
            self.head = 1
        self._q[self.head - 1] = x
        if self.tail == 0:
            self.tail = 1
        self.count += 1
        return None

    def madd(self, *args, _list=None):
        """Append several objects. ``_list`` is R's ``.list``."""
        items = _collect(args, _list)
        n_args = len(items)
        if n_args == 0:
            return None
        capacity = len(self._q)
        if self.count + n_args > capacity:
            capacity = self._resize_at_least(self.count + n_args)
        n_until_wrap = capacity - self.head
        if n_until_wrap >= n_args:
            for offset, item in enumerate(items, start=1):
                self._q[self.head + offset - 1] = item
            self.head += n_args
        else:
            if n_until_wrap > 0:
                for offset, item in enumerate(items[:n_until_wrap]):
                    self._q[self.head + offset] = item
            n_after = n_args - n_until_wrap
            for offset, item in enumerate(items[n_until_wrap:]):
                self._q[offset] = item
            self.head = self.head + n_args - capacity
        if self.tail == 0:
            self.tail = 1
        self.count += n_args
        return None

    def remove(self, missing=_MISSING):
        """Take the oldest object. An empty queue returns ``missing``."""
        if missing is _MISSING:
            missing = self.missing_default
        if self.count == 0:
            return missing
        capacity = len(self._q)
        value = self._q[self.tail - 1]
        self._q[self.tail - 1] = None
        if self.tail == self.head:
            self.tail = 0
            self.head = 0
        else:
            self.tail += 1
            if self.tail > capacity:
                self.tail -= capacity
        self.count -= 1
        if capacity > self.init and self.count <= capacity / 4:
            self._resize_at_least(self.count + 1)
        return value

    def mremove(self, n, missing=_MISSING):
        """Take the next ``n`` objects, oldest first.

        Slots past the end of the queue are ``missing``. An empty queue
        raises ``ValueError``, matching R's zero-length replacement.
        """
        if missing is _MISSING:
            missing = self.missing_default
        n = _as_integer(n)
        if n < 1:
            raise ValueError("`n` must be at least 1.")
        if self.count == 0:
            raise ValueError("replacement has length zero")
        capacity = len(self._q)
        values = [None] * n
        run_length = min(n, capacity - self.tail + 1)
        if self.head >= self.tail:
            run_length = min(run_length, self.head - self.tail + 1)
        run_idxs = range(self.tail, self.tail + run_length)
        for offset, idx in enumerate(run_idxs):
            values[offset] = self._q[idx - 1]
            self._q[idx - 1] = None
        total_filled = run_length
        remaining = n - run_length
        self.count -= run_length
        self.tail += run_length
        if self.count == 0:
            self.head = 0
            self.tail = 0
        elif self.tail > capacity:
            self.tail = 1
        if remaining > 0 and self.count != 0 and self.tail <= self.head:
            run_length = min(remaining, self.head)
            for offset in range(run_length):
                values[total_filled + offset] = self._q[offset]
                self._q[offset] = None
            total_filled += run_length
            remaining -= run_length
            self.count -= run_length
            self.tail += run_length
            if self.count == 0:
                self.head = 0
                self.tail = 0
        if remaining > 0:
            for offset in range(total_filled, n):
                values[offset] = missing
        if capacity > self.init and self.count <= capacity / 4:
            self._resize_at_least(self.count + 1)
        return values

    def peek(self, missing=_MISSING):
        """Return the oldest object without removing it."""
        if missing is _MISSING:
            missing = self.missing_default
        if self.count == 0:
            return missing
        return self._q[self.tail - 1]

    def reset(self):
        """Drop every object and restore the starting capacity."""
        self._q = [None] * self.init
        self.head = 0
        self.tail = 0
        self.count = 0
        return None

    def size(self):
        """Return how many objects are in the queue."""
        return self.count

    def as_list(self):
        """Return the objects from oldest to newest."""
        if self.count == 0:
            return []
        return self._as_list(self.count)

    def _as_list(self, size):
        if size < self.count:
            raise ValueError("Can't return list smaller than number of items.")
        capacity = len(self._q)
        low_tail = self.tail
        if self.head < self.tail:
            low_tail = self.tail - capacity
        new_q = [None] * size
        position = 0
        cursor = low_tail
        while cursor <= self.head:
            index = (cursor - 1) % capacity + 1
            new_q[position] = self._q[index - 1]
            position += 1
            cursor += 1
        return new_q

    def _resize(self, n):
        if n < self.count:
            raise ValueError(
                f"Can't shrink smaller than number of items ({self.count})."
            )
        if n <= 0:
            raise ValueError("Can't shrink smaller than one.")
        if len(self._q) == n:
            return n
        if self.count == 0:
            self._q = [None] * n
            return n
        self._q = self._as_list(n)
        self.tail = 1
        self.head = self.count
        return n

    def _resize_at_least(self, n):
        new_capacity = self.init
        if new_capacity < 1:
            new_capacity = 1
        while new_capacity < n:
            new_capacity *= 2
        return self._resize(new_capacity)


def _length(init):
    if isinstance(init, bool) or init is None:
        raise ValueError("invalid 'length' argument")
    if isinstance(init, float):
        if not math.isfinite(init) or not init.is_integer():
            raise ValueError("invalid 'length' argument")
        init = int(init)
    if not isinstance(init, int) or init < 0:
        raise ValueError("invalid 'length' argument")
    return init


def _as_integer(n):
    if isinstance(n, bool) or n is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(n, int):
        return n
    if isinstance(n, float):
        if not math.isfinite(n):
            raise ValueError("missing value where TRUE/FALSE needed")
        return int(math.trunc(n))
    raise ValueError("`n` must be at least 1.")


def _collect(args, _list):
    items = list(args)
    if _list is None:
        return items
    if isinstance(_list, dict):
        items.extend(_list.values())
        return items
    if isinstance(_list, (list, tuple)):
        items.extend(_list)
        return items
    raise TypeError(".list must be a list")
