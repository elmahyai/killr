"""R's R_qsort_I, CACM algorithm 347 as shipped in R 4.5 qsort-body.c.

Bounds `i` and `j` are 1-based and inclusive, matching the C entry point.
"""

from __future__ import annotations


def r_qsort_i(values, index, i: int, j: int) -> None:
    """Sort `values[i-1:j]` ascending and permute `index` the same way."""
    il = [0] * 40
    iu = [0] * 40
    ratio = 0.375
    origin = i
    depth = 1

    def value_at(pos: int) -> float:
        return values[pos - 1]

    def set_value(pos: int, item: float) -> None:
        values[pos - 1] = item

    def index_at(pos: int) -> int:
        return index[pos - 1]

    def set_index(pos: int, item: int) -> None:
        index[pos - 1] = item

    step = "L10"
    while True:
        if step == "L10":
            if i < j:
                if ratio < 0.5898437:
                    ratio += 0.0390625
                else:
                    ratio -= 0.21875
                step = "L20"
                continue
            step = "L80"
            continue
        if step == "L20":
            left = i
            pivot_at = i + int((j - i) * ratio)
            pivot_index = index_at(pivot_at)
            pivot = value_at(pivot_at)
            if value_at(i) > pivot:
                set_index(pivot_at, index_at(i))
                set_index(i, pivot_index)
                pivot_index = index_at(pivot_at)
                set_value(pivot_at, value_at(i))
                set_value(i, pivot)
                pivot = value_at(pivot_at)
            right = j
            if value_at(j) < pivot:
                set_index(pivot_at, index_at(j))
                set_index(j, pivot_index)
                pivot_index = index_at(pivot_at)
                set_value(pivot_at, value_at(j))
                set_value(j, pivot)
                pivot = value_at(pivot_at)
                if value_at(i) > pivot:
                    set_index(pivot_at, index_at(i))
                    set_index(i, pivot_index)
                    pivot_index = index_at(pivot_at)
                    set_value(pivot_at, value_at(i))
                    set_value(i, pivot)
                    pivot = value_at(pivot_at)
            while True:
                right -= 1
                while value_at(right) > pivot:
                    right -= 1
                held_index = index_at(right)
                held = value_at(right)
                left += 1
                while value_at(left) < pivot:
                    left += 1
                if left > right:
                    break
                set_index(right, index_at(left))
                set_index(left, held_index)
                set_value(right, value_at(left))
                set_value(left, held)
            depth += 1
            if right - i <= j - left:
                il[depth] = left
                iu[depth] = j
                j = right
            else:
                il[depth] = i
                iu[depth] = right
                i = left
            step = "AFTER"
            continue
        if step == "L80":
            if depth == 1:
                return
            i = il[depth]
            j = iu[depth]
            depth -= 1
            step = "AFTER"
            continue
        if step == "AFTER":
            if j - i > 10:
                step = "L20"
                continue
            if i == origin:
                step = "L10"
                continue
            i -= 1
            step = "L100"
            continue
        while True:
            i += 1
            if i == j:
                step = "L80"
                break
            pivot_index = index_at(i + 1)
            pivot = value_at(i + 1)
            if value_at(i) <= pivot:
                continue
            cursor = i
            while True:
                set_index(cursor + 1, index_at(cursor))
                set_value(cursor + 1, value_at(cursor))
                cursor -= 1
                if not pivot < value_at(cursor):
                    break
            set_index(cursor + 1, pivot_index)
            set_value(cursor + 1, pivot)
        continue
