import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiny.req import Delayed, MissingArg, MissingDotError, SilentError, req
from shiny.values import (
    NA,
    NA_character_,
    NA_integer_,
    NA_real_,
    ShinyError,
    Vector,
    WithClass,
)


class DataFrame:
    def __init__(self) -> None:
        self.nrow = 0
        self.ncol = 0


def fmt_double(value) -> str:
    if isinstance(value, type(NA)):
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if value == math.inf:
        return "Inf"
    if value == -math.inf:
        return "-Inf"
    if value == 0.0 and math.copysign(1.0, value) < 0:
        return "-0"
    return format(value, ".15g")


def fmt_complex(value) -> str:
    real = fmt_double(value.real)
    imag = value.imag
    if imag == 0.0 and math.copysign(1.0, imag) < 0:
        return real + "-" + fmt_double(0.0) + "i"
    if math.copysign(1.0, imag) < 0 and imag != 0.0:
        return real + "-" + fmt_double(abs(imag)) + "i"
    return real + "+" + fmt_double(imag) + "i"


def tok(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, DataFrame):
        return f"DF:{value.nrow}x{value.ncol}"
    classes = ()
    names = None
    if isinstance(value, WithClass):
        classes = value.classes
        names = getattr(value.value, "names", None)
        value = value.value
    if isinstance(value, Vector):
        if not classes:
            classes = value.classes
        if names is None:
            names = getattr(value, "names", None)
        data = list(value.data)
        kind = value.mode
    elif isinstance(value, bool):
        data = [value]
        kind = "logical"
    elif isinstance(value, int):
        data = [value]
        kind = "integer"
    elif isinstance(value, float):
        data = [value]
        kind = "double"
    elif isinstance(value, str):
        data = [value]
        kind = "character"
    elif isinstance(value, complex):
        data = [value]
        kind = "complex"
    elif isinstance(value, (bytes, bytearray)):
        data = list(value)
        kind = "raw"
    elif type(value).__name__ == "Missing":
        data = [value]
        kind = value.mode
    elif isinstance(value, list):
        data = value
        kind = "list"
    else:
        return "OTHER"
    suffix = ""
    if classes:
        suffix += "{" + ",".join(classes) + "}"
    if names is not None:
        suffix += "{names:" + "|".join(names) + "}"
    if kind == "raw":
        return "RAW:" + "|".join(f"{byte:02x}" for byte in data) + suffix
    if kind == "complex":
        return "CPLX:" + "|".join(fmt_complex(item) for item in data) + suffix
    if kind == "character":
        parts = ["<NA>" if type(item).__name__ == "Missing" else item for item in data]
        return "C:" + "|".join(parts) + suffix
    if kind == "logical":
        parts = []
        for item in data:
            if type(item).__name__ == "Missing":
                parts.append("NA")
            elif item is True:
                parts.append("TRUE")
            else:
                parts.append("FALSE")
        return "L:" + "|".join(parts) + suffix
    if kind == "integer":
        parts = ["NA" if type(item).__name__ == "Missing" else str(item) for item in data]
        return "I:" + "|".join(parts) + suffix
    if kind == "double":
        return "D:" + "|".join(fmt_double(item) for item in data) + suffix
    if kind == "list":
        return f"LIST:{len(data)}{suffix}"
    return "OTHER"


def grab(fn) -> str:
    try:
        return "OK " + tok(fn())
    except SilentError as exc:
        return "ERR " + "/".join(exc.classes) + "|" + exc.message
    except MissingDotError as exc:
        return "ERR " + "/".join(exc.classes) + "|" + exc.message
    except ShinyError as exc:
        return "ERR simpleError/error/condition|" + str(exc)
    except Exception as exc:
        return "ERR simpleError/error/condition|" + str(exc)


def btn(value):
    return WithClass(value, ("shinyActionButtonValue",))


def named_true():
    value = Vector([True], "logical")
    value.names = ["a"]
    return value


def named_progress():
    value = Vector(["progress"], "character")
    value.names = ["a"]
    return value


def named_cancel_true():
    value = Vector([True], "logical")
    value.names = ["cancelOutput"]
    return value


def one() -> str:
    parts = [
        grab(lambda: req()),
        grab(lambda: req(cancelOutput=True)),
        grab(lambda: req(1.0, True)),
        grab(lambda: req(1, 2, 3)),
        grab(lambda: req(1.0, 2.0, 3.0)),
        grab(lambda: req(0.0)),
        grab(lambda: req(0)),
        grab(lambda: req(-0.0)),
        grab(lambda: req(" ")),
        grab(lambda: req("ab", "cd")),
        grab(lambda: req(Vector([False, True], "logical"))),
        grab(lambda: req(True, "progress")),
        grab(lambda: req(Vector(["", "a"], "character"))),
        grab(lambda: req(Vector([NA_character_, "a"], "character"))),
        grab(lambda: req(Vector(["  ", NA_character_], "character"))),
        grab(lambda: req(b"\x00")),
        grab(lambda: req(bytes([0, 1]))),
        grab(lambda: req(0j)),
        grab(lambda: req(1 + 1j)),
        grab(lambda: req(math.inf)),
        grab(lambda: req(-math.inf)),
        grab(lambda: req([])),
        grab(lambda: req([False])),
        grab(lambda: req([None])),
        grab(lambda: req(5.0)),
        grab(lambda: req(Vector([1, 2, 3], "integer"), Vector([4, 5, 6], "integer"))),
        grab(lambda: req(named_true())),
        grab(lambda: req(Vector([0.0, NA_real_], "double"), 1.0)),
        grab(lambda: req(Vector([float("nan"), 1.0], "double"))),
        grab(lambda: req(btn(1))),
        grab(lambda: req(btn("a"))),
        grab(lambda: req(btn("0.0"))),
        grab(lambda: req(WithClass(Vector([1], "integer"), ("factor",)))),
        grab(lambda: req(DataFrame())),
        grab(lambda: req(1.0, cancelOutput="progress")),
        grab(lambda: req(0.0, cancelOutput="progress")),
        grab(lambda: req(1.0, 2.0, cancelOutput=False)),
        grab(lambda: req(0.0, "progress")),
        grab(lambda: req(*range(1, 1001))),
        grab(lambda: req(1.0, 2.0, 3.0)),
        grab(lambda: req(False)),
        grab(lambda: req(None)),
        grab(lambda: req("")),
        grab(lambda: req(True, False)),
        grab(lambda: req(NA)),
        grab(lambda: req(NA_integer_)),
        grab(lambda: req(NA_real_)),
        grab(lambda: req(NA_character_)),
        grab(lambda: req(Vector([], "character"))),
        grab(lambda: req(Vector([], "logical"))),
        grab(lambda: req(Vector([], "double"))),
        grab(lambda: req(b"")),
        grab(lambda: req(Vector([False, False], "logical"))),
        grab(lambda: req(Vector(["", ""], "character"))),
        grab(lambda: req(float("nan"))),
        grab(lambda: req(Vector([float("nan"), float("nan")], "double"))),
        grab(lambda: req(btn(0))),
        grab(lambda: req(btn(0.0))),
        grab(lambda: req(btn("0"))),
        grab(lambda: req(btn(NA_integer_))),
        grab(lambda: req(WithClass(Vector(["boom"], "character"), ("try-error",)))),
        grab(lambda: req(WithClass(Vector([NA_integer_], "integer"), ("factor",)))),
        grab(lambda: req(WithClass(Vector([], "integer"), ("factor",)))),
        grab(lambda: req(Vector([False], "logical"))),
        grab(lambda: req(False)),
        grab(lambda: req(False, cancelOutput=True)),
        grab(lambda: req("", cancelOutput="progress")),
        grab(lambda: req(1.0, False, cancelOutput="progress")),
        grab(lambda: req("ok", "", cancelOutput="progress")),
        grab(lambda: req(False, cancelOutput="TRUE")),
        grab(lambda: req(False, cancelOutput=1)),
        grab(lambda: req(False, cancelOutput=NA)),
        grab(lambda: req(False, cancelOutput=None)),
        grab(lambda: req(False, cancelOutput=Vector([True, True], "logical"))),
        grab(lambda: req(False, cancelOutput=Vector([True], "logical"))),
        grab(lambda: req(False, cancelOutput=WithClass(True, ("foo",)))),
        grab(lambda: req(False, cancelOutput=named_progress())),
        grab(lambda: req(False, cancelOutput=WithClass("progress", ("foo",)))),
        grab(lambda: req(False, cancelOutput=named_cancel_true())),
        grab(lambda: req(False, True)),
        grab(lambda: req(False, True)),
        grab(lambda: req(1.0, False)),
        grab(lambda: req(btn(Vector([0, 1], "integer")))),
        grab(lambda: req(True, Delayed(_boom))),
        grab(lambda: req(1.0, MissingArg())),
        grab(lambda: req(MissingArg(), 1.0)),
    ]

    hit = [0.0]

    def bump():
        hit[0] = hit[0] + 1.0
        return hit[0]

    hit[0] = 0.0
    res = grab(lambda: req(None, Delayed(bump)))
    parts.append(res + f" hit={int(hit[0])}")
    hit[0] = 0.0
    res = grab(lambda: req(Delayed(bump)))
    parts.append(res + f" hit={int(hit[0])}")
    hit[0] = 0.0

    def mark_true():
        hit[0] = hit[0] + 1.0
        return True

    res = grab(lambda: req(Delayed(mark_true)))
    parts.append(res + f" hit={int(hit[0])}")
    hit[0] = 0.0

    def mark_nine():
        hit[0] = hit[0] + 1.0
        return 9.0

    res = grab(lambda: req(True, Delayed(mark_nine)))
    parts.append(res + f" hit={int(hit[0])}")
    hit[0] = 0.0

    def boom():
        hit[0] = hit[0] + 1.0
        raise RuntimeError("boom")

    res = grab(lambda: req(False, Delayed(boom)))
    parts.append(res + f" hit={int(hit[0])}")
    hit[0] = 0.0

    def later():
        hit[0] = hit[0] + 1.0
        return 1.0

    res = grab(lambda: req(MissingArg(), Delayed(later)))
    parts.append(res + f" hit={int(hit[0])}")
    return "\n".join(parts)


def _boom():
    raise RuntimeError("boom")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
