"""Raw concordance1 / concordance2 counts from the survconc crate.

One untimed call, then the median of 20 calls timed with std::time::Instant
inside the crate. speedup is the R Sys.time() median divided by that median.
"""

from __future__ import annotations

import statistics

import numpy as np

from survconc import concordance1, concordance1_ms, concordance2, concordance2_ms


def fmt(values) -> str:
    return ",".join(f"{float(v):.17g}" for v in np.asarray(values, dtype=float).reshape(-1))


def btree(n: int) -> np.ndarray:
    ranks = np.zeros(n, dtype=np.int64)
    if n < 1:
        return ranks
    yet_to_do = np.arange(n)
    depth = n.bit_length() - 1
    start = 1 << depth
    lastrow_length = 1 + n - start
    indx = np.arange(0, 2 * lastrow_length, 2)
    ranks[yet_to_do[indx]] = start + np.arange(indx.size)
    yet_to_do = np.delete(yet_to_do, indx)
    while start > 1:
        start //= 2
        indx = np.arange(0, 2 * start, 2)
        indx = indx[indx < yet_to_do.size]
        ranks[yet_to_do[indx]] = start + np.arange(indx.size)
        yet_to_do = np.delete(yet_to_do, indx)
    return ranks


def pack_right(time, status, x, wt):
    time = np.asarray(time, dtype=float)
    status = np.asarray(status, dtype=float)
    x = np.asarray(x, dtype=float)
    wt = np.asarray(wt, dtype=float)
    order = np.lexsort((-status, time))
    y = np.column_stack((time[order], status[order]))
    ux = np.sort(np.unique(x))
    index = (btree(ux.size)[np.searchsorted(ux, x[order])] - 1).astype(np.int32)
    return ("right", y, wt[order], index, int(ux.size))


def pack_count(start, stop, status, x, wt):
    start = np.asarray(start, dtype=float)
    stop = np.asarray(stop, dtype=float)
    status = np.asarray(status, dtype=float)
    x = np.asarray(x, dtype=float)
    wt = np.asarray(wt, dtype=float)
    y = np.column_stack((start, stop, status))
    ux = np.sort(np.unique(x))
    index = (btree(ux.size)[np.searchsorted(ux, x)] - 1).astype(np.int32)
    sort_stop = np.lexsort((status, -stop)).astype(np.int32)
    sort_start = np.argsort(-start, kind="stable").astype(np.int32)
    return ("count", y, wt, index, int(ux.size), sort_stop, sort_start)


time = np.array([1, 2, 2, 2, 3, 4, 4, 4, 5, 2], dtype=float)
status = np.array([1, 0, 1, 0, 1, 0, 1, 1, 0, 1], dtype=float)
x = np.array([5, 5, 4, 4, 3, 3, 7, 6, 5, 4], dtype=float)
s = np.array(["a", "a", "b", "b", "a", "b", "a", "b", "a", "b"])
w = np.array([1, 2, 1, 1, 2, 1, 1, 0.5, 1, 1], dtype=float)
start = np.array([0, 0, 1, 2, 0, 3, 1, 2, 0, 4], dtype=float)
stop = np.array([2, 3, 4, 4, 5, 6, 6, 7, 8, 9], dtype=float)
cstatus = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0], dtype=float)
xc = np.array([3, 5, 2, 4, 1, 5, 3, 2, 4, 1], dtype=float)
cs = np.array(["u", "v", "u", "v", "u", "u", "v", "v", "u", "v"])
ones = np.ones(time.size, dtype=float)

n_large = 20000
i_large = np.arange(n_large)
large_time = (i_large + 1).astype(float)
large_status = np.where(i_large % 4 == 0, 0.0, 1.0)
large_x = i_large.astype(float)
large_wt = 1 + (i_large % 5) * 0.25
large_start = i_large.astype(float)
large_stop = large_start + n_large

cases = [
    pack_right(time, status, x, ones),
    pack_right(time, status, x, w),
    pack_right(time[s == "a"], status[s == "a"], x[s == "a"], ones[s == "a"]),
    pack_right(time[s == "b"], status[s == "b"], x[s == "b"], ones[s == "b"]),
    pack_count(start, stop, cstatus, xc, ones),
    pack_count(start, stop, cstatus, xc, w),
    pack_count(start[cs == "u"], stop[cs == "u"], cstatus[cs == "u"], xc[cs == "u"], ones[cs == "u"]),
    pack_count(start[cs == "v"], stop[cs == "v"], cstatus[cs == "v"], xc[cs == "v"], ones[cs == "v"]),
    pack_count([0, 0, 2], [2, 3, 4], [1, 1, 1], [1, 2, 0], [1, 1, 1]),
    pack_count([0, 0, 1], [5, 3, 4], [0, 1, 1], [1, 2, 0], [1, 1, 1]),
    pack_right(large_time, large_status, large_x, large_wt),
    pack_count(large_start, large_stop, large_status, large_x, large_wt),
]


def invoke(case, timed: bool):
    kind = case[0]
    if kind == "right":
        _, y, wt, index, ntree = case
        if timed:
            return concordance1_ms(y, wt, index, ntree)
        return concordance1(y, wt, index, ntree), 0.0
    _, y, wt, index, ntree, sort_stop, sort_start = case
    if timed:
        return concordance2_ms(y, wt, index, ntree, sort_stop, sort_start)
    return concordance2(y, wt, index, ntree, sort_stop, sort_start), 0.0


def one():
    return [invoke(case, False)[0] for case in cases]


def one_ms() -> float:
    total = 0.0
    for case in cases:
        _, ms = invoke(case, True)
        total += ms
    return total


raw = one()
elapsed = [one_ms() for _ in range(20)]
print("\n".join(fmt(row) for row in raw))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
