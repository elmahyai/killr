import math
import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iterators.core import DataFrame, IteratorError, iter, nextElem
from iterators.isplit import NA, Atomic, Factor, RList, factor, isplit


def rhex(value):
    if value is NA:
        return "NA"
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    negative = math.copysign(1.0, value) < 0.0
    mantissa, exponent = abs(value).hex().split("p")
    prefix, fraction = mantissa.split(".")
    fraction = fraction.rstrip("0")
    if fraction == "":
        body = prefix + "p" + exponent
    else:
        body = prefix + "." + fraction + "p" + exponent
    return ("-" if negative else "") + body


def fmt_scalar(value, kind):
    if kind == "character":
        return "NA" if value is NA else value
    if kind == "logical":
        if value is NA:
            return "NA"
        return "TRUE" if value else "FALSE"
    if kind == "integer":
        return "NA" if value is NA else str(int(value))
    if kind == "double":
        return rhex(value)
    return "NA" if value is NA else str(value)


def fmt_atomic(values, kind, names):
    body = ",".join(fmt_scalar(value, kind) for value in values)
    text = f"{kind}:{body}"
    if names is not None:
        shown = []
        for name in names:
            shown.append("NA" if name is NA else str(name))
        text += ";names=" + ",".join(shown)
    return text


def fmt_factor(obj):
    codes = ",".join("NA" if code is NA else str(int(code)) for code in obj.codes)
    return "factor:" + codes + "/" + ",".join(obj.levels)


def fmt_frame(frame):
    columns = []
    for index, name in enumerate(frame.names):
        columns.append(
            name + "=" + fmt_atomic(frame.columns[name], frame.kinds[index], None)
        )
    return "df:" + ",".join(frame.row_names) + "|" + "|".join(columns)


def fmt_list(obj):
    parts = []
    for index, element in enumerate(obj.elements):
        body = fmt_value(element)
        if obj.names is None:
            parts.append("[" + body + "]")
        else:
            name = obj.names[index]
            if name is NA:
                name = "NA"
            parts.append("[" + str(name) + "=" + body + "]")
    return "list:" + "".join(parts)


def fmt_value(value):
    if value is None:
        return "NULL"
    if isinstance(value, Factor):
        return fmt_factor(value)
    if isinstance(value, DataFrame):
        return fmt_frame(value)
    if isinstance(value, RList):
        return fmt_list(value)
    if isinstance(value, Atomic):
        return fmt_atomic(value.values, value.kind, value.names)
    if isinstance(value, bool):
        return fmt_atomic([value], "logical", None)
    if isinstance(value, int):
        return fmt_atomic([value], "integer", None)
    if isinstance(value, float):
        return fmt_atomic([value], "double", None)
    if isinstance(value, str):
        return fmt_atomic([value], "character", None)
    raise TypeError(type(value))


def fmt_group(group):
    parts = []
    for index, value in enumerate(group.key):
        body = group.key_kinds[index] + ":" + fmt_scalar(value, group.key_kinds[index])
        if group.key_names is None:
            parts.append("[" + body + "]")
        else:
            name = group.key_names[index]
            if name is NA:
                name = "NA"
            parts.append("[" + str(name) + "=" + body + "]")
    return "V(" + fmt_value(group.value) + ")K(" + "".join(parts) + ")"


def take(it, k=24):
    out = []
    for _ in range(k):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                group = nextElem(it)
                message = None
            except IteratorError as exc:
                group = None
                message = exc.message
        for item in caught:
            out.append("W:" + str(item.message))
        if message is not None:
            out.append(message)
            break
        out.append(fmt_group(group))
    return out


def err(fn):
    try:
        fn()
        return "OK"
    except IteratorError as exc:
        return exc.message


def step(it):
    try:
        return fmt_group(nextElem(it))
    except IteratorError as exc:
        return exc.message


def one():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    groups = factor(["b", "a", "b", "a", "b"], levels=["b", "a", "c"])
    left = isplit([10, 20, 30, 40], ["a", "b", "a", "b"])
    right = isplit([10, 20, 30, 40], ["a", "b", "a", "b"])
    base = isplit([5, 6], ["a", "b"])
    same = "SAME" if iter(base) is base else "DIFF"
    frame = DataFrame(
        {"p": [1, 2, 3, 4], "q": ["w", "x", "w", "x"]},
        row_names=["r1", "r2", "r3", "r4"],
    )
    levels = factor(["x", "w", "x", "w"], levels=["w", "x", "y"])
    narrow = DataFrame({"p": [1, 2]})
    parts = [
        *take(isplit(values, groups, drop=False)),
        *take(isplit(values, groups, drop=True)),
        *take(isplit([1.0, 2.0, 3.0, 4.0], ["b", "a", "b", "a"])),
        *take(isplit([9, 8, 7, 6], [1, NA, 2, 1])),
        *take(isplit([9.0, 8.0, 7.0, 6.0, 5.0], [1.0, NA, float("nan"), 1.0, 2.0])),
        *take(isplit([9, 8, 7, 6], [True, False, NA, True])),
        *take(isplit([9.0, 8.0, 7.0], [-0.0, 0.0, 1.0])),
        *take(isplit([1.0, 2.0, 3.0], [float("inf"), float("-inf"), float("inf")])),
        *take(isplit([7.0, 8.0, 9.0], [10.0, 2.0, 10.0])),
        *take(isplit(list(range(1, 7)), ["b", "A", "a", "B", "10", "2"])),
        *take(isplit([7.0, 8.0, 9.0], [1.0 + 2**-52, 1.0, 2.0])),
        *take(isplit(Atomic([1, 2, 3, 4], "integer", ["a", "b", "c", "d"]), ["z", "y", "z", "y"])),
        *take(isplit(RList([10, 20, 30, 40], ["a", "b", "c", "d"]), ["u", "v", "u", "v"])),
        *take(isplit(np.arange(1, 7).reshape((2, 3), order="F"), ["a", "b"])),
        *take(isplit([10.0, 20.0, 30.0, 40.0], np.array(["a", "b", "a", "b"]).reshape((2, 2), order="F"))),
        *take(isplit(factor(["p", "q", "p", "q"]), ["a", "b", "a", "b"])),
        *take(isplit(values, {"g": ["u", "u", "v", "v", "u"], "h": [2.0, 1.0, 2.0, 1.0, 2.0]})),
        *take(isplit(list(range(1, 5)), RList([["a", "b", "a", "b"], [1.0, 1.0, 2.0, 2.0]], ["", "g"]))),
        *take(isplit([1.0, 2.0, 3.0, 4.0], DataFrame({"a": ["u", "u", "v", "v"], "b": [1.0, 2.0, 1.0, 2.0]}))),
        *take(isplit(frame, ["w", "x", "w", "x"])),
        *take(isplit(frame, levels, drop=False)),
        *take(isplit(frame, levels, drop=True)),
        *take(isplit(narrow, ["a", "b", "a", "a"])),
        *take(isplit(Atomic([], "double"), factor(["a", "b"]))),
        *take(isplit(Atomic([], "integer"), Factor([], ["a", "b"]))),
        *take(isplit(None, "a")),
        *take(isplit([1, 2], ["a", "b", "a"])),
        *take(isplit([1, 2, 3], ["a", "b"])),
        *take(isplit(list(range(1, 5)), [["a", "b", "a", "b"], ["u", "v"]])),
        *take(isplit(list(range(1, 7)), [["a", "b", "a"], ["u", "v", "w", "x"]])),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), drop=0)),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), drop=2)),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), drop=NA)),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), drop=[])),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), drop="TRUE")),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), drop=[True, False])),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), dr=True)),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), True)),
        *take(isplit([1, 2], factor(["a", "a"], levels=["a", "b"]), foo=1)),
        *take(isplit([1, 2, 3], None)),
        *take(isplit([1, 2, 3], [NA, NA, NA])),
        *take(isplit([1, 2, 3], Atomic([], "character"))),
        *take(isplit(f=["a", "b"])),
        step(left),
        step(right),
        step(left),
        same,
        *take(base),
        err(lambda: isplit([1, 2, 3], RList([]))),
        err(lambda: isplit([1, 2, 3])),
        err(lambda: isplit()),
        err(lambda: isplit([1, 2], ["a", "b"], d=1, dr=2)),
    ]
    return "||".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
