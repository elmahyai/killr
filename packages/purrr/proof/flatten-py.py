import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from purrr.flatten import (
    NA,
    Character,
    Complex,
    Double,
    Integer,
    List,
    Logical,
    Raw,
    flatten,
)


def enc_name(name):
    if name is NA:
        return "NA"
    if name == "":
        return "E"
    return "S" + name


def enc_names(value):
    if value is None or value.names is None:
        return "*"
    return ",".join(enc_name(name) for name in value.names)


def enc_real(value):
    if value is NA:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if value == math.inf:
        return "Inf"
    if value == -math.inf:
        return "-Inf"
    if value == 0.0 and math.copysign(1.0, value) < 0.0:
        return "-0"
    return format(float(value), ".17g")


def encode(value):
    if value is None:
        return "NULL"
    if isinstance(value, List):
        elements = []
        for element in value.values:
            elements.append("NULL" if element is None else encode(element))
        return "L{" + enc_names(value) + "}:" + "|".join(elements)
    if (
        isinstance(value, Integer)
        and value.attrs
        and value.attrs.get("class") == "factor"
    ):
        bits = ["NA" if item is NA else str(item) for item in value.values]
        levels = ",".join(value.attrs["levels"])
        return "F" + ",".join(bits) + "L" + levels + "{" + enc_names(value) + "}"
    if isinstance(value, Character):
        bits = ["NA" if item is NA else "S" + item for item in value.values]
        return "C" + ",".join(bits) + "{" + enc_names(value) + "}"
    if isinstance(value, Logical):
        bits = []
        for item in value.values:
            if item is NA:
                bits.append("NA")
            elif item:
                bits.append("T")
            else:
                bits.append("F")
        return "G" + ",".join(bits) + "{" + enc_names(value) + "}"
    if isinstance(value, Integer):
        bits = ["NA" if item is NA else str(item) for item in value.values]
        return "I" + ",".join(bits) + "{" + enc_names(value) + "}"
    if isinstance(value, Complex):
        bits = []
        for item in value.values:
            if item is NA:
                bits.append("NA")
            else:
                bits.append(enc_real(item.real) + "+" + enc_real(item.imag))
        return "Z" + ",".join(bits) + "{" + enc_names(value) + "}"
    if isinstance(value, Raw):
        bits = [f"{item:02x}" for item in value.values]
        return "X" + ",".join(bits) + "{" + enc_names(value) + "}"
    if isinstance(value, Double):
        return (
            "D"
            + ",".join(enc_real(item) for item in value.values)
            + "{"
            + enc_names(value)
            + "}"
        )
    raise TypeError(type(value).__name__)


def build(n=5000):
    values = []
    names = []
    for i in range(1, n + 1):
        if i % 17 == 0:
            names.append("")
        elif i % 19 == 0:
            names.append(NA)
        else:
            names.append(f"p{i}")
        slot = i % 11
        if slot == 0:
            values.append(None)
        elif slot == 1:
            values.append(Double([i / 3, -0.0], ["a", "b"]))
        elif slot == 2:
            values.append(Integer([i, NA, i % 7], ["x", "y", "z"]))
        elif slot == 3:
            values.append(Logical([True, False, NA]))
        elif slot == 4:
            values.append(Character([f"v{i}", NA], ["s", "t"]))
        elif slot == 5:
            values.append(Double([i / 7] if i % 2 == 0 else [NA]))
        elif slot == 6:
            values.append(List([List([Integer([i])]), None, Double([i + 0.5])]))
        elif slot == 7:
            values.append(Raw([i % 256, 255]))
        elif slot == 8:
            values.append(Complex([complex(-0.0, float(i))]))
        elif slot == 9:
            values.append(Double([]))
        else:
            values.append(Double([float("nan"), math.inf, -math.inf, i / 11]))
    return List(values, names)


manual = List(
    [
        List([Double([1.0]), Double([2.0])]),
        List([Double([3.0]), Double([4.0])]),
    ]
)
names_case = List(
    [List([Double([1.0])], ["x"]), Integer([2, 3]), None],
    ["a", "b", "c"],
)
scalar_parent = List(
    [List([Double([1.0])]), List([Double([2.0])])],
    ["a", "b"],
)
child = List(
    [List([Double([1.0])], ["x"]), List([Double([2.0])], ["y"])],
    ["a", "b"],
)
blank = List([Double([], []), Double([1.0])])
na_child = List([Double([1.0], ["a"]), Double([2.0], [NA])])
parent_na = List([Double([1.0]), Double([2.0], ["z"])], [NA, "b"])
long_scalar = List([Integer([1, 2]), Double([3.0])], ["a", "b"])
no_names = List([Integer([1, 2]), Integer([3, 4])])
nested_null = List([List([Double([1.0]), None, Double([2.0])])])
factor = Integer([2, 1], attrs={"class": "factor", "levels": ["a", "b"]})
factor_direct = List([factor])
factor_kept = List([List([factor])])
columns = List([Integer([1, 2]), Integer([3, 4])], ["a", "b"])
inner_named = List([List([Double([1.0, 2.0], ["a", "b"])])])
empty = List([])
nulls = List([None, None])
only_empty_named = List([Double([], [])])
special = List(
    [
        Double([NA, float("nan"), math.inf, -math.inf], ["a", "b", "c", "d"]),
        Complex([NA]),
        Raw([0, 255]),
        Character([NA]),
        Logical([True, NA]),
    ]
)
big = build()


def one():
    return (
        flatten(manual),
        flatten(names_case),
        flatten(scalar_parent),
        flatten(child),
        flatten(blank),
        flatten(na_child),
        flatten(parent_na),
        flatten(long_scalar),
        flatten(no_names),
        flatten(nested_null),
        flatten(factor_direct),
        flatten(factor_kept),
        flatten(columns),
        flatten(inner_named),
        flatten(empty),
        flatten(nulls),
        flatten(only_empty_named),
        flatten(special),
        flatten(big),
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

shown = " ".join(encode(piece) for piece in value)
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
