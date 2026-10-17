"""pracma sorting routines. These are the published algorithms, not a library sort."""

from __future__ import annotations

import math
import time
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.interp_support import is_numeric_value, stopifnot


def _numeric(a) -> np.ndarray:
    if not is_numeric_value(a):
        raise PracmaError("Argument 'a' must be a non-empty numeric vector.")
    return np.array(np.asarray(a, dtype=float).reshape(-1), copy=True)


def _comp(u, v) -> bool:
    return bool(u < v)


def bubbleSort(a):
    values = _numeric(a)
    n = values.size
    if n <= 1:
        return values
    for _i in range(n):
        for j in range(1, n):
            current = values[j]
            if _comp(values[j], values[j - 1]):
                values[j] = values[j - 1]
                values[j - 1] = current
    return values


def insertionSort(a):
    values = _numeric(a)
    n = values.size
    if n <= 1:
        return values
    for i in range(1, n):
        held = values[i]
        j = i
        while j >= 1 and values[j - 1] > held:
            values[j] = values[j - 1]
            j -= 1
        values[j] = held
    return values


def selectionSort(a):
    values = _numeric(a)
    n = values.size
    if n <= 1:
        return values
    for i in range(n - 1):
        chosen = i
        for j in range(i + 1, n):
            if values[j] < values[chosen]:
                chosen = j
        values[chosen], values[i] = values[i], values[chosen]
    return values


def _r_round(value: float) -> int:
    return int(np.round(value))


def shellSort(a, f=2.3):
    values = _numeric(a)
    if not is_numeric_value(f) or np.asarray(f).size != 1 or float(np.asarray(f).reshape(-1)[0]) <= 1:
        raise PracmaError("The retracting factor 'f' must be a numeric scalar > 1.0")
    factor = float(np.asarray(f).reshape(-1)[0])
    n = values.size
    if n <= 1:
        return values
    gap = n // 2
    while gap >= 1:
        for i in range(gap, n):
            held = values[i]
            j = i
            while values[j - gap] > held:
                values[j] = values[j - gap]
                j -= gap
                if j < gap:
                    break
            values[j] = held
        gap = _r_round(gap / factor)
    return values


def heapSort(a):
    values = _numeric(a)
    warnings.warn("Function 'heapSort' not yet implemented.", stacklevel=2)
    return values


def mergeOrdered(a, b):
    left = np.asarray(a, dtype=float).reshape(-1)
    right = np.asarray(b, dtype=float).reshape(-1)
    merged = np.zeros(left.size + right.size)
    i = 0
    j = 0
    while True:
        if left[i] <= right[j]:
            merged[i + j] = left[i]
            i += 1
            if i >= left.size:
                merged[i + j :] = right[j:]
                break
        else:
            merged[i + j] = right[j]
            j += 1
            if j >= right.size:
                merged[i + j :] = left[i:]
                break
    return merged


def mergeSort(a, m=10):
    stopifnot(is_numeric_value(m), "is.numeric(m)")
    stopifnot(np.asarray(m).size == 1, "length(m) == 1")
    limit = float(np.asarray(m).reshape(-1)[0])
    stopifnot(math.floor(limit) == math.ceil(limit), "floor(m) == ceiling(m)")
    values = _numeric(a)
    n = values.size
    if n <= int(limit):
        return insertionSort(values)
    half = n // 2
    return mergeOrdered(mergeSort(values[:half]), mergeSort(values[half:]))


def quickSort(a, m=3):
    values = np.asarray(a, dtype=float).reshape(-1)
    n = values.size
    threshold = int(m)
    if n <= threshold:
        return insertionSort(values)
    pivot = (values[0] + values[1]) / 2
    return np.concatenate([quickSort(values[values <= pivot], m=threshold), quickSort(values[values > pivot], m=threshold)])


def quickSortx(a, m=25):
    values = np.array(np.asarray(a, dtype=float).reshape(-1), copy=True)
    n = values.size
    if n <= m:
        return insertionSort(values)
    i = 0
    j = n
    pivot = values[n - 1]
    while True:
        while i < n and values[i] < pivot:
            i += 1
        while j > 1 and values[j - 2] >= pivot:
            j -= 1
        if i >= j - 1:
            break
        values[i], values[j - 2] = values[j - 2], values[i]
    if i == 0:
        return np.concatenate([np.array([values[n - 1]]), quickSortx(values[: n - 1])])
    if j == n:
        return np.concatenate([quickSortx(values[: n - 1]), np.array([values[n - 1]])])
    return np.concatenate(
        [quickSortx(values[:i]), np.array([values[n - 1]]), quickSortx(values[i : n - 1])]
    )


def is_sorted(a):
    """Python name of is.sorted. NA comparisons follow R's any()."""
    values = np.asarray(a, dtype=float).reshape(-1)
    if values.size < 2:
        return np.array([1.0])
    if np.any(np.isnan(values)):
        return np.array([np.nan])
    if np.any(values[1:] < values[:-1]):
        return np.array([0.0])
    return np.array([1.0])


def testSort(n=1000):
    count = int(n)
    if count >= 1e5:
        warnings.warn("n quite large: This will take some time!", stacklevel=2)
    sample = np.random.random(count)
    print("Test Begin...", flush=True)
    print("Do not test bubble sort (too slow).\n", flush=True)
    names = [
        ("Insertion sort", insertionSort, "Insertion sort successful.\n", "Insertion sort test FAILED.\n"),
        ("Selection sort", selectionSort, "Selection sort successful.\n", "Selection sort test FAILED.\n"),
        ("Shellsort", shellSort, "Shell sort successful.\n", "Shell sort test FAILED.\n"),
        ("Mergesort", mergeSort, "Merge sort successful.\n", "Merge sort test FAILED.\n"),
        ("Heapsort", heapSort, "heap sort successful.\n", "Heap sort test FAILED.\n"),
        ("Quicksort", quickSort, "Quicksort successful.\n", "Quicksort test FAILED.\n"),
    ]
    for label, routine, ok, failed in names:
        started = time.perf_counter()
        ordered = routine(sample.copy())
        elapsed = time.perf_counter() - started
        print(f"{label}: Elapsed time =  {elapsed} secs", flush=True)
        flag = is_sorted(ordered)
        if flag.size and flag[0] == 1:
            print(ok, flush=True)
        else:
            print(failed, flush=True)
    print("Test End", flush=True)
    return None
