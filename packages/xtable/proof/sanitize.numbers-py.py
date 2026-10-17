import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.sanitize import NA, Strings
from xtable.sanitize_numbers import sanitize_numbers

BASE = [
    "1e5",
    "1E10",
    "-2.5e+10",
    "1.2e-03",
    "not",
    "1e5e6",
    NA,
    "",
    "$1e5$",
    "1e+05",
    "1.0e00",
    "3e-0",
    "1e-3",
    "10000",
    "a-b",
    "1-2",
    "-1",
]
BASE_NAMES = [chr(ord("a") + i) for i in range(len(BASE))]
base = Strings(BASE, BASE_NAMES)


def plain(value):
    if value is NA:
        return None
    if isinstance(value, Strings):
        return [plain(item) for item in value]
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def message_of(expr):
    try:
        expr()
        return [None]
    except ValueError as exc:
        return [str(exc)]


def one():
    both = sanitize_numbers(base, "latex", True, True)
    return {
        "default": sanitize_numbers(base, "latex"),
        "html": sanitize_numbers(base, "html"),
        "html_opts": sanitize_numbers(base, "html", True, True),
        "neg": sanitize_numbers(base, "latex", math_style_negative=True),
        "exp": sanitize_numbers(base, "latex", math_style_exponents=True),
        "both": both,
        "numeric": sanitize_numbers([1e5, 1000, -1], "latex", True, True),
        "numeric_html": [sanitize_numbers(1e5, "html")],
        "named": both,
        "named_names": both.names,
        "empty": sanitize_numbers([], "latex"),
        "single": sanitize_numbers("1e5", "latex", False, True),
        "err_type_len": message_of(
            lambda: sanitize_numbers(base, ["latex", "html"])
        ),
        "err_type_na": message_of(lambda: sanitize_numbers(base, NA)),
        "err_neg_na": message_of(
            lambda: sanitize_numbers("1", "latex", math_style_negative=NA)
        ),
        "err_exp_na": message_of(
            lambda: sanitize_numbers("1", "latex", math_style_exponents=NA)
        ),
        "err_exp_str": message_of(
            lambda: sanitize_numbers("1e5", "latex", math_style_exponents="$$")
        ),
        "err_neg_len": message_of(
            lambda: sanitize_numbers("1", "latex", math_style_negative=[True, False])
        ),
        "exp_num": sanitize_numbers("1e5", "latex", False, 1),
        "neg_chr": sanitize_numbers("-1", "latex", "TRUE", "FALSE"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
