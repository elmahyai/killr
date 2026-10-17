import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiny.css import validateCssUnit
from shiny.values import (
    NA,
    NA_character_,
    NA_complex_,
    NA_integer_,
    NA_real_,
    Missing,
    ShinyError,
    Vector,
)


def encode(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, list):
        return "L(" + ",".join(encode(item) for item in value) + ")"
    if isinstance(value, str):
        text = value.replace("\n", "\\n").replace("\t", "\\t")
        return "C(" + text + ")"
    if isinstance(value, Missing):
        if value.mode == "integer":
            return "NA_integer_"
        if value.mode == "character":
            return "NA_character_"
        if value.mode == "complex":
            return "NA_complex_"
        if value.mode == "double":
            return "NA_real_"
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        return "D(" + str(value) + ")"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return "I(" + str(value) + ")"
    if isinstance(value, complex):
        if math.isnan(value.real) or math.isnan(value.imag):
            return "NA_complex_"
        return "CX"
    return "O"


def show(fn) -> str:
    try:
        return encode(fn())
    except ShinyError as exc:
        msg = str(exc).replace("\n", "\\n").replace("\t", "\\t")
        return "ERR " + msg


def one() -> str:
    calls = [
        lambda: validateCssUnit(None),
        lambda: validateCssUnit(NA),
        lambda: validateCssUnit(NA_integer_),
        lambda: validateCssUnit(NA_real_),
        lambda: validateCssUnit(NA_character_),
        lambda: validateCssUnit(NA_complex_),
        lambda: validateCssUnit(float("nan")),
        lambda: validateCssUnit(Vector([], "character")),
        lambda: validateCssUnit(Vector([], "double")),
        lambda: validateCssUnit(Vector([], "integer")),
        lambda: validateCssUnit(Vector([], "logical")),
        lambda: validateCssUnit(Vector([NA, NA], "logical")),
        lambda: validateCssUnit(Vector([1.0, 2.0], "double")),
        lambda: validateCssUnit(Vector([1, 2, 3], "integer")),
        lambda: validateCssUnit(Vector(["1px", "2px"], "character")),
        lambda: validateCssUnit(False),
        lambda: validateCssUnit(True),
        lambda: validateCssUnit([]),
        lambda: validateCssUnit([1]),
        lambda: validateCssUnit([NA]),
        lambda: validateCssUnit([None]),
        lambda: validateCssUnit([float("nan")]),
        lambda: validateCssUnit([NA_real_]),
        lambda: validateCssUnit([Vector([NA_real_, 1.0], "double")]),
        lambda: validateCssUnit(""),
        lambda: validateCssUnit(" "),
        lambda: validateCssUnit("auto"),
        lambda: validateCssUnit("AUTO"),
        lambda: validateCssUnit("inherit"),
        lambda: validateCssUnit("fit-content"),
        lambda: validateCssUnit("fit-content(20px)"),
        lambda: validateCssUnit("10%"),
        lambda: validateCssUnit("400px"),
        lambda: validateCssUnit(400.0),
        lambda: validateCssUnit(400),
        lambda: validateCssUnit(400.0),
        lambda: validateCssUnit(1.5),
        lambda: validateCssUnit(-10.0),
        lambda: validateCssUnit(-0.0),
        lambda: validateCssUnit(0.0),
        lambda: validateCssUnit(0),
        lambda: validateCssUnit(float("inf")),
        lambda: validateCssUnit(float("-inf")),
        lambda: validateCssUnit(1e-4),
        lambda: validateCssUnit(1e5),
        lambda: validateCssUnit(100000),
        lambda: validateCssUnit(math.pi),
        lambda: validateCssUnit(float(2**53)),
        lambda: validateCssUnit(float(2**53 + 2)),
        lambda: validateCssUnit(float(2**60)),
        lambda: validateCssUnit(1e15),
        lambda: validateCssUnit(1e16),
        lambda: validateCssUnit(1e-20),
        lambda: validateCssUnit(1e308),
        lambda: validateCssUnit(0.00012),
        lambda: validateCssUnit(-0.00012),
        lambda: validateCssUnit(1 / 3),
        lambda: validateCssUnit(0.3),
        lambda: validateCssUnit(9.99999999999999e-05),
        lambda: validateCssUnit("007"),
        lambda: validateCssUnit("100000"),
        lambda: validateCssUnit("00"),
        lambda: validateCssUnit("0"),
        lambda: validateCssUnit("0.0"),
        lambda: validateCssUnit(".5"),
        lambda: validateCssUnit(".5px"),
        lambda: validateCssUnit("0.5px"),
        lambda: validateCssUnit("10.0px"),
        lambda: validateCssUnit("5."),
        lambda: validateCssUnit("5.px"),
        lambda: validateCssUnit("1.0"),
        lambda: validateCssUnit("1."),
        lambda: validateCssUnit("calc(100% - 10px)"),
        lambda: validateCssUnit("calc()"),
        lambda: validateCssUnit("calc("),
        lambda: validateCssUnit("calc())"),
        lambda: validateCssUnit("calc(a\nb)"),
        lambda: validateCssUnit("1in"),
        lambda: validateCssUnit("2.5vmin"),
        lambda: validateCssUnit("10vh"),
        lambda: validateCssUnit("1ch"),
        lambda: validateCssUnit("1em"),
        lambda: validateCssUnit("1ex"),
        lambda: validateCssUnit("1rem"),
        lambda: validateCssUnit("1pt"),
        lambda: validateCssUnit("1pc"),
        lambda: validateCssUnit("1cm"),
        lambda: validateCssUnit("1mm"),
        lambda: validateCssUnit("1vw"),
        lambda: validateCssUnit("1vmax"),
        lambda: validateCssUnit("1%"),
        lambda: validateCssUnit("01px"),
        lambda: validateCssUnit("10.5%"),
        lambda: validateCssUnit(".5%"),
        lambda: validateCssUnit("foo"),
        lambda: validateCssUnit("+5"),
        lambda: validateCssUnit("+5px"),
        lambda: validateCssUnit("1e2"),
        lambda: validateCssUnit("1e2px"),
        lambda: validateCssUnit("-10px"),
        lambda: validateCssUnit("-1"),
        lambda: validateCssUnit("10PX"),
        lambda: validateCssUnit("10px "),
        lambda: validateCssUnit(" 10px"),
        lambda: validateCssUnit("auto "),
        lambda: validateCssUnit("vmin"),
        lambda: validateCssUnit("10v"),
        lambda: validateCssUnit("\t10px"),
        lambda: validateCssUnit("10\n"),
        lambda: validateCssUnit("\u0661\u0662\u0663"),
        lambda: validateCssUnit(1 + 0j),
        lambda: validateCssUnit(b"\x00"),
        lambda: validateCssUnit(b""),
        lambda: validateCssUnit("999999999999999999"),
        lambda: validateCssUnit("9" * 400),
    ]
    return "\n".join(show(fn) for fn in calls)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
