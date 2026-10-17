import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from purrr.discard import NA, Character, Double, Integer, Logical, discard


def build(n=8000):
    values = []
    names = []
    for i in range(1, n + 1):
        names.append(f"v{i}")
        residue = i % 17
        if residue == 0:
            values.append(NA)
        elif residue == 1:
            values.append(float("nan"))
        elif residue == 2:
            values.append(math.inf)
        elif residue == 3:
            values.append(-math.inf)
        elif residue == 4:
            values.append(-0.0)
        else:
            values.append((i % 97) / 7)
    return Double(values, names)


def enc_real(value):
    if value is NA:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if value == math.inf:
        return "Inf"
    if value == -math.inf:
        return "-Inf"
    if isinstance(value, float) and value == 0.0 and math.copysign(1.0, value) < 0.0:
        return "-0"
    return format(float(value), ".17g")


def enc_names(value):
    if value is None or value.names is None:
        return "*"
    if not value.names:
        return ""
    parts = []
    for name in value.names:
        if name is NA:
            parts.append("NA")
        elif name == "":
            parts.append("E")
        else:
            parts.append("S" + name)
    return ",".join(parts)


def encode_ex(ex):
    element = ex.values[0]
    flag = element.values[0].values[0]
    word = "NA" if flag is NA else "TRUE" if flag else "FALSE"
    numbers = ",".join(str(int(item)) for item in element.values[1].values)
    return (
        f"L({enc_names(ex)}){{L({enc_names(element)}){{"
        f"logical(*)[{word}];integer(*)[{numbers}]}}}}"
    )


def encode_mask(value):
    body = ",".join(enc_real(item) for item in value.values)
    return f"double({enc_names(value)})[{body}]"


def encode_extra(value):
    body = ",".join(str(int(item)) for item in value.values)
    return f"integer({enc_names(value)})[{body}]"


def encode_chr(value):
    body = ",".join("NA" if item is NA else "S" + item for item in value.values)
    return f"character({enc_names(value)})[{body}]"


def encode_big(value):
    parts = []
    for name, item in zip(value.names, value.values):
        parts.append(f"{name}:{enc_real(item)}")
    return ";".join(parts)


def finite_above_five(value):
    if value is NA or (isinstance(value, float) and not math.isfinite(value)):
        return False
    return value > 5


x = build()


def one():
    ex = discard(
        [
            {"a": True, "b": Integer([4, 5, 6])},
            {"a": False, "b": Integer([7, 8, 9])},
            {"a": True, "b": Integer([1, 2, 3])},
        ],
        "a",
    )
    mask = discard(
        Double([1.0, -0.0, NA, 4.0], ["a", "b", "c", "d"]),
        Logical([True, False, NA, True]),
    )
    extra = discard(Integer(list(range(1, 7))), lambda v, lim: v > lim, 3)
    chars = discard(
        Character(["x", "y", ""], ["a", "b", "c"]),
        lambda s: len(s) > 0,
    )
    big = discard(x, finite_above_five)
    return ex, mask, extra, chars, big


example, mask, extra, chars, big = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = (
    "EX "
    + encode_ex(example)
    + " MASK "
    + encode_mask(mask)
    + " EXTRA "
    + encode_extra(extra)
    + " CHR "
    + encode_chr(chars)
    + " BIG "
    + encode_big(big)
)
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
