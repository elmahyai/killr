import math
import statistics
import string
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiny.need import Delayed, Invisible, NeedError, need
from shiny.values import (
    NA,
    NA_character_,
    NA_complex_,
    NA_integer_,
    NA_real_,
    Missing,
    ShinyError,
    Vector,
    WithClass,
)


def fmt_double(value) -> str:
    if isinstance(value, Missing):
        return "NA"
    if math.isnan(value):
        return "NaN"
    if value == math.inf:
        return "Inf"
    if value == -math.inf:
        return "-Inf"
    if value == 0.0 and math.copysign(1.0, value) < 0.0:
        return "-0"
    if math.isfinite(value) and value == math.floor(value) and abs(value) < 1e15:
        return str(int(value))
    return format(value, ".15g")


def fmt_complex(value) -> str:
    if isinstance(value, Missing):
        return "<NA>"
    real = fmt_double(value.real) if not isinstance(value.real, Missing) else "<NA>"
    if math.isnan(value.real) and not isinstance(value, Missing):
        real = "NaN"
    imag = value.imag
    if imag == 0.0:
        return real + "+0i"
    if math.isnan(imag):
        return real + "+NaNi"
    if imag < 0.0:
        return real + "-" + fmt_double(-imag) + "i"
    return real + "+" + fmt_double(imag) + "i"


def tok(value) -> str:
    if value is None:
        return "NULL"
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
    elif isinstance(value, Missing):
        data = [value]
        kind = value.mode
    else:
        return "OTHER"
    suffix = ""
    if classes:
        suffix += "{" + ",".join(classes) + "}"
    if names is not None:
        suffix += "{names:" + "|".join(names) + "}"
    prefix = f"n={len(data)} "
    if kind == "raw":
        body = "|".join(f"{byte:02x}" for byte in data)
        return prefix + "RAW:" + body + suffix
    if kind == "complex":
        return prefix + "CPLX:" + "|".join(fmt_complex(item) for item in data) + suffix
    if kind == "character":
        parts = ["<NA>" if isinstance(item, Missing) else item for item in data]
        return prefix + "C:" + "|".join(parts) + suffix
    if kind == "logical":
        parts = []
        for item in data:
            if isinstance(item, Missing):
                parts.append("NA")
            elif item is True:
                parts.append("TRUE")
            else:
                parts.append("FALSE")
        return prefix + "L:" + "|".join(parts) + suffix
    if kind == "integer":
        parts = ["NA" if isinstance(item, Missing) else str(item) for item in data]
        return prefix + "I:" + "|".join(parts) + suffix
    if kind == "double":
        return prefix + "D:" + "|".join(fmt_double(item) for item in data) + suffix
    return "OTHER"


def grab(fn) -> str:
    try:
        value = fn()
    except NeedError as exc:
        return "ERR " + "/".join(exc.classes) + "|" + exc.message
    except ShinyError as exc:
        return "ERR simpleError/error/condition|" + str(exc)
    except Exception as exc:
        return "ERR simpleError/error/condition|" + str(exc)
    visible = 1
    if isinstance(value, Invisible):
        visible = 0
        value = value.value
    return f"OK vis={visible} {tok(value)}"


def btn(value):
    return WithClass(value, ("shinyActionButtonValue",))


def factor(labels):
    levels = []
    codes = []
    for lab in labels:
        if lab is None or isinstance(lab, Missing):
            codes.append(NA_integer_)
        else:
            if lab not in levels:
                levels.append(lab)
            codes.append(levels.index(lab) + 1)
    obj = WithClass(Vector(codes, "integer"), ("factor",))
    obj.levels = levels
    return obj


def named_message():
    value = Vector(["x", "y"], "character")
    value.names = ["a", "b"]
    return value


def classed_z():
    return WithClass(Vector(["z"], "character"), ("foo",))


def one() -> str:
    parts = [
        grab(lambda: need()),
        grab(lambda: need(1 + 1)),
        grab(lambda: need(None)),
        grab(lambda: need(None, label="input$x")),
        grab(lambda: need(1, label="input$x")),
        grab(lambda: need(None, message="custom message")),
        grab(lambda: need(1, message="custom message")),
        grab(lambda: need(None, message="explicit", label="ignored")),
        grab(lambda: need(None, False)),
        grab(lambda: need(True, False)),
        grab(lambda: need(False, False)),
        grab(lambda: need("", False)),
        grab(lambda: need(Vector([], "character"), False)),
        grab(lambda: need(Vector([], "logical"), False)),
        grab(lambda: need(Vector([], "double"), False)),
        grab(lambda: need(Vector([], "integer"), False)),
        grab(lambda: need(Vector([], "complex"), False)),
        grab(lambda: need(b"", False)),
        grab(lambda: need(Vector([NA_real_], "double"), False)),
        grab(lambda: need(Vector([False], "logical"), False)),
        grab(lambda: need(NA, False)),
        grab(lambda: need(NA_integer_, False)),
        grab(lambda: need(NA_real_, False)),
        grab(lambda: need(NA_complex_, False)),
        grab(lambda: need(NA_character_, False)),
        grab(lambda: need(Vector([NA, NA, False], "logical"), False)),
        grab(lambda: need(Vector([False], "logical"), False)),
        grab(lambda: need(WithClass(Vector(["boom"], "character"), ("try-error",)), False)),
        grab(lambda: need(0.0, False)),
        grab(lambda: need(0, False)),
        grab(lambda: need(-0.0, False)),
        grab(lambda: need(Vector(list(range(1, 11)), "integer"), False)),
        grab(lambda: need(Vector(list(string.ascii_uppercase), "character"), False)),
        grab(lambda: need("NA", False)),
        grab(lambda: need(" ", False)),
        grab(lambda: need(Vector([NA, NA, True], "logical"), False)),
        grab(lambda: need(Vector([False, False, True], "logical"), False)),
        grab(lambda: need(None, label=Vector(["a", "b"], "character"))),
        grab(lambda: need(None, label=1)),
        grab(lambda: need(None, label=1)),
        grab(lambda: need(None, label=True)),
        grab(lambda: need(None, label=False)),
        grab(lambda: need(None, label=NA)),
        grab(lambda: need(None, label=NA_character_)),
        grab(lambda: need(None, label=None)),
        grab(lambda: need(None, label=Vector([], "character"))),
        grab(lambda: need(None, label=Vector([], "double"))),
        grab(lambda: need(None, label=Vector([NA_character_, "x"], "character"))),
        grab(lambda: need(None, label=1.5)),
        grab(lambda: need(None, label=math.inf)),
        grab(lambda: need(None, label=float("nan"))),
        grab(lambda: need(None, label=-0.0)),
        grab(lambda: need(None, label=1j)),
        grab(lambda: need(None, label=bytes([65]))),
        grab(lambda: need(None, "hello", "ignored")),
        grab(lambda: need(None, Vector(["a", "b"], "character"))),
        grab(lambda: need(None, Vector([], "character"))),
        grab(lambda: need(None, "")),
        grab(lambda: need(None, "  ")),
        grab(lambda: need(None, NA)),
        grab(lambda: need(None, NA_character_)),
        grab(lambda: need(None, NA_integer_)),
        grab(lambda: need(None, NA_real_)),
        grab(lambda: need(None, float("nan"))),
        grab(lambda: need(None, message=None)),
        grab(lambda: need(1, message=None)),
        grab(lambda: need(None, named_message())),
        grab(lambda: need(None, label=Vector(["field", "other"], "character"))),
        grab(lambda: need(None, label=factor(["field", NA, "field"]))),
        grab(lambda: need(None, Vector([False, True], "logical"))),
        grab(lambda: need(None, 3.5)),
        grab(lambda: need(None, 3)),
        grab(lambda: need(None, 0.0)),
        grab(lambda: need(None, 0)),
        grab(lambda: need(None, -0.0)),
        grab(lambda: need(None, 1j)),
        grab(lambda: need(None, bytes([65]))),
        grab(lambda: need(None, b"")),
        grab(lambda: need(" ", "space")),
        grab(lambda: need(float("nan"), "nan")),
        grab(lambda: need(math.inf, "inf")),
        grab(lambda: need(-math.inf, "ninf")),
        grab(lambda: need([], "list")),
        grab(lambda: need([False], "listfalse")),
        grab(lambda: need(DataFrame(), "df")),
        grab(lambda: need(Vector(["", ""], "character"), "blank")),
        grab(lambda: need(Vector([NA_character_, "a"], "character"), "mixc")),
        grab(lambda: need(Vector(["  ", NA_character_], "character"), "ws")),
        grab(lambda: need(bytes([0]), "raw")),
        grab(lambda: need(b"", "rawe")),
        grab(lambda: need(0j, "c0")),
        grab(lambda: need(factor(["a"]), "fac")),
        grab(lambda: need(factor([NA]), "facna")),
        grab(lambda: need(factor([]), "fac0")),
        grab(lambda: need(btn(0), "btn")),
        grab(lambda: need(btn(1), "btn")),
        grab(lambda: need(btn(0.0), "btn")),
        grab(lambda: need(btn("0"), "btn")),
        grab(lambda: need(btn("a"), "btn")),
        grab(lambda: need(btn("0.0"), "btn")),
        grab(lambda: need(btn(NA_integer_), "btn")),
        grab(lambda: need(btn(Vector([0, 1], "integer")), "btn")),
        grab(lambda: need(None, label=Vector([
            1e-4, 100000.0, 10000.0, 0.00012, 99999.0, -1.25, -100000.0,
            math.inf, -math.inf, float("nan"), NA_real_,
        ], "double"))),
        grab(lambda: need(None, label=Vector([
            1j, 1 - 2j, 1e-4 + 1e5j, NA_complex_, complex(float("nan"), 1.0),
            complex(-0.0, -0.0), complex(2.0, -0.0), -1j,
        ], "complex"))),
        grab(lambda: need(None, label=bytes([0, 10, 65, 255]))),
        grab(lambda: need(None, label=[
            "a", NA, 1, False, None,
            Vector([], "character"), Vector([], "double"), Vector([], "integer"),
            Vector([], "logical"), Vector([], "complex"), b"",
        ])),
        grab(lambda: need(None, label=Vector([True, False, NA], "logical"))),
        grab(lambda: need(None, label="")),
        grab(lambda: need(None, label=" ")),
        grab(lambda: need(None, label=2147483647)),
        grab(lambda: need(None, classed_z())),
        grab(lambda: need(None, label=classed_z())),
        grab(lambda: need(1.0, expr=None)),
        grab(lambda: need(None, lab="field")),
        grab(lambda: need(None, mes="hello")),
        grab(lambda: need(None, m="hello")),
        grab(lambda: need(None, l="field")),
        grab(lambda: need(e=None, message="z")),
        grab(lambda: need(None, me="A", la="B")),
        grab(lambda: need(None, message="a", m="b")),
        grab(lambda: need(None, "a", "b", "c")),
        grab(lambda: need(None, "a", "b", "c", "d")),
        grab(lambda: need(None, "a", "b", 4)),
        grab(lambda: need(foo="bar")),
        grab(lambda: need(message="x")),
        grab(lambda: need(label="L")),
        grab(lambda: need(None, Vector(["a", NA_character_], "character"))),
    ]

    hit = [0]

    def add(amount, value):
        def run():
            hit[0] += amount
            return value
        return run

    hit[0] = 0
    res = grab(lambda: need(Delayed(add(1, True)), message=Delayed(add(10, "m"))))
    parts.append(res + f" hit={hit[0]}")
    hit[0] = 0

    def boom():
        raise RuntimeError("nope")

    res = grab(lambda: need(Delayed(add(1, False)), message=Delayed(boom)))
    parts.append(res + f" hit={hit[0]}")
    hit[0] = 0
    res = grab(lambda: need(Delayed(add(1, None)), label=Delayed(add(10, "L"))))
    parts.append(res + f" hit={hit[0]}")
    hit[0] = 0
    res = grab(lambda: need(Delayed(add(1, 1))))
    parts.append(res + f" hit={hit[0]}")
    hit[0] = 0

    def stop_no():
        hit[0] += 1
        raise RuntimeError("no")

    res = grab(lambda: need(True, message="explicit", label=Delayed(stop_no)))
    parts.append(res + f" hit={hit[0]}")
    hit[0] = 0
    res = grab(lambda: need(True, label=Delayed(add(1, "L"))))
    parts.append(res + f" hit={hit[0]}")
    hit[0] = 0
    res = grab(lambda: need(False, message=Delayed(add(1, "m"))))
    parts.append(res + f" hit={hit[0]}")
    hit[0] = 0

    def stop_lab():
        raise RuntimeError("lab")

    res = grab(lambda: need(Delayed(add(1, True)), label=Delayed(stop_lab)))
    parts.append(res + f" hit={hit[0]}")
    return "\n".join(parts)


class DataFrame:
    def __init__(self) -> None:
        self.nrow = 0
        self.ncol = 0


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
