import math
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from purrr.prepend import (
    NA,
    Character,
    Complex,
    Double,
    Integer,
    List,
    Logical,
    Raw,
    prepend,
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
        return "D" + ",".join(enc_real(item) for item in value.values) + "{" + enc_names(value) + "}"
    raise TypeError(type(value).__name__)


n = 100000
big = Double([i / 3 for i in range(1, n + 1)], [f"v{i}" for i in range(1, n + 1)])
special = Double(
    [-0.0, NA, float("nan"), math.inf, -math.inf, 1.5],
    ["a", "b", "c", "d", "e", "f"],
)


def one():
    lists = List([Integer([1]), Integer([2]), Integer([3])])
    ex_a = prepend(lists, "a")
    ex_b = prepend(lists, ["a", "b"], before=3)
    ex_c = prepend([], lists)
    front = prepend(Integer([1, 2, 3], ["p", "q", "r"]), Logical([True, False, NA]))
    chars = prepend(
        "z",
        Double([1e-4, 1e5, 1 / 3, NA, float("nan"), math.inf]),
    )
    comp = prepend(Complex([1 + 2j, 1 - 2j]), 0 + 1j)
    rawv = prepend(Raw([0, 15]), Raw([255]))
    lst = prepend(
        List([Double([1.0]), None, Character(["q"])], ["a", "b", "c"]),
        List([Integer([2])], ["d"]),
        before=2,
    )
    frac = prepend(Integer([1, 2, 3, 4, 5]), 99.0, before=1.9)
    sign = prepend(Double([-0.0, 1.0]), -0.0)
    mid = prepend(big, special, before=n // 2)
    return (ex_a, ex_b, ex_c, front, chars, comp, rawv, lst, frac, sign, mid)


warnings.filterwarnings("ignore", category=UserWarning)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

shown = " ".join(encode(piece) for piece in value)
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
