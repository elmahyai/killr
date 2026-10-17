import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiny.truthy import isTruthy
from shiny.values import (
    NA,
    NA_character_,
    NA_complex_,
    NA_integer_,
    NA_real_,
    ShinyError,
    Vector,
    WithClass,
)


def show(value):
    try:
        return "TRUE" if isTruthy(value) else "FALSE"
    except ShinyError as exc:
        return "ERR " + str(exc)


def one():
    def btn(value):
        return WithClass(value, ("shinyActionButtonValue",))

    cases = [
        None,
        False,
        True,
        "",
        " ",
        "0",
        "NA",
        Vector([], "character"),
        Vector([], "logical"),
        Vector([], "double"),
        Vector([], "integer"),
        Vector([], "complex"),
        b"",
        NA,
        NA_integer_,
        NA_real_,
        NA_complex_,
        NA_character_,
        Vector([NA, NA, False], "logical"),
        False,
        0.0,
        0,
        Vector([1, 2, 3], "integer"),
        Vector(["a", "b"], "character"),
        Vector([NA, NA, True], "logical"),
        Vector([False, False, True], "logical"),
        WithClass(Vector(["boom"], "character"), ("try-error",)),
        [],
        Vector([NA_real_], "double"),
        Vector([False], "logical"),
        float("nan"),
        float("inf"),
        float("-inf"),
        0j,
        b"\x00",
        Vector([1], "integer"),
        Vector([NA_integer_], "integer"),
        Vector([], "integer"),
        [],
        btn(0),
        btn(1),
        btn(0.0),
        btn("0"),
        btn("a"),
        btn("0.0"),
        Vector(["", ""], "character"),
        Vector(["", "a"], "character"),
        Vector([NA_character_, ""], "character"),
        Vector([NA_character_, "a"], "character"),
        Vector([NA, False], "logical"),
        Vector([False, False], "logical"),
        Vector([0.0, NA_real_], "double"),
        Vector([float("nan"), float("nan")], "double"),
        Vector([float("nan"), 1.0], "double"),
        btn(Vector([0, 1], "integer")),
        Vector([False], "logical"),
        -0.0,
        WithClass(["err"], ("try-error",)),
        Vector(["  ", NA_character_], "character"),
        bytes([0, 1]),
    ]
    return "\n".join(show(case) for case in cases)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
