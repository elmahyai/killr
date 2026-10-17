import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/htmltools")

from htmltools.escape import NA, is_na
from htmltools.html import HTML

example = Path("/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/HTML-python.txt")
marked = HTML("I like <u>turtles</u>")
joined = HTML("a", "b", noWS="before")
example.write_text(
    'HTML("I like <u>turtles</u>") returns ' + marked + ".\n"
    'HTML("a", "b", .noWS = "before") returns ' + joined + ".\n"
)

piece = [
    "I like <u>turtles</u>",
    "a < b & 'c'",
    "caf\u00e9",
    "plain",
    NA,
    "",
    "line1\nline2",
    "a\"b\\c",
]
text = piece * 400


def encode_nows(no_ws):
    if no_ws is None:
        return {"type": "null"}
    if is_na(no_ws):
        return {"type": "character", "value": None}
    if isinstance(no_ws, str):
        return {"type": "character", "value": no_ws}
    if isinstance(no_ws, bool):
        return {"type": "logical", "value": no_ws}
    if isinstance(no_ws, int):
        return {"type": "integer", "value": no_ws}
    if isinstance(no_ws, float):
        return {"type": "double", "value": no_ws}
    if isinstance(no_ws, (list, tuple)):
        if len(no_ws) == 0:
            return {"type": "character", "value": []}
        values = [None if is_na(item) else item for item in no_ws]
        if len(values) == 1:
            return {"type": "character", "value": values[0]}
        return {"type": "character", "value": values}
    return {"type": type(no_ws).__name__, "value": no_ws}


def pack(value):
    return {
        "text": str(value),
        "html": True if value.html else False,
        "class": list(value.r_class),
        "noWS": encode_nows(value.noWS),
    }


def message(call):
    try:
        call()
    except ValueError as exc:
        return str(exc)
    raise AssertionError("expected an error")


def one():
    return {
        "example": pack(HTML("I like <u>turtles</u>")),
        "concat": pack(HTML("a", "b", "c")),
        "vec": pack(HTML(["a", "b"], "c", "d")),
        "markup": pack(HTML("a < b & 'c'")),
        "numbers": pack(HTML([1e-4, 1e5, 10000.0, 0.00015, 2e5, NA, float("nan"), float("inf"), float("-inf"), -0.0, 1 / 3])),
        "integer": pack(HTML([100000, 1, NA])),
        "logical": pack(HTML([True, False, NA])),
        "mixed_int": pack(HTML([True, 1])),
        "mixed_dbl": pack(HTML([True, 1, 1.5])),
        "mixed_chr": pack(HTML([True, "a"])),
        "na_mid": pack(HTML(["a", NA, "b"])),
        "empty_mid": pack(HTML("a", "", "b")),
        "null_text": pack(HTML(None)),
        "null_dot": pack(HTML("a", None)),
        "null_then": pack(HTML(None, "a")),
        "null_null": pack(HTML(None, None)),
        "char0": pack(HTML([])),
        "empty": pack(HTML("")),
        "utf": pack(HTML("caf\u00e9", "\u2603")),
        "newline": pack(HTML("a\nb", "c\td")),
        "ws": pack(HTML("  a  ", "  b")),
        "complex": pack(HTML([1 + 2j, 1 - 2j])),
        "seq_text": pack(HTML([1, 2, 3])),
        "big": pack(HTML(text)),
        "nows_before": pack(HTML("x", noWS="before")),
        "nows_pair": pack(HTML("x", noWS=["before", "after"])),
        "nows_out": pack(HTML("x", noWS="outside")),
        "nows_null": pack(HTML("x", noWS=None)),
        "nows_empty": pack(HTML("x", noWS=[])),
        "nows_int": pack(HTML("x", noWS=1)),
        "nows_na": pack(HTML("x", noWS=NA)),
        "named": pack(HTML("a", foo="b", bar="c")),
        "dot_seq": pack(HTML("p", [1, 2, 3, 4, 5])),
        "dot_rev": pack(HTML("p", [5, 4, 3, 2, 1])),
        "dot_neg": pack(HTML("p", [-2, -1, 0, 1, 2])),
        "dot_gap": pack(HTML("p", [1, 2, 4])),
        "dot_same": pack(HTML("p", [1, 1])),
        "dot_dbl_seq": pack(HTML("p", [1.0, 2.0, 3.0])),
        "dot_dbl": pack(HTML("p", [1e-4, 1e5, NA, float("nan")])),
        "dot_log": pack(HTML("p", [True, False, NA])),
        "dot_chr": pack(HTML("p", ["x", "y"])),
        "dot_esc": pack(HTML("p", ['a"b', "c\\d", "e\nf"])),
        "dot_na_chr": pack(HTML("p", ["a", NA])),
        "dot_mixed": pack(HTML("p", [True, "a"])),
        "dot_two": pack(HTML(["a", "b"], ["c", "d"])),
        "dot_empty": pack(HTML("a", [])),
        "dot_cpx": pack(HTML("p", [1 + 2j, 1 - 2j])),
        "dot_list": pack(HTML("a", {"b": 1, "c": "x"})),
        "dot_list_names": pack(HTML("a", {"a b": 1, "if": 2, "ok": "z"})),
        "dot_list_unnamed": pack(HTML("a", [[1], ["x"]])),
        "already": pack(HTML(HTML("a<b>", noWS="before"))),
        "named_flag": pack(HTML("a", **{".named": True})),
        "named_flag_value": pack(HTML("a", "b", **{".named": True})),
        "ignore_all": pack(HTML("a", "b", **{".ignore_empty": "all"})),
        "homonyms_keep": pack(HTML("a", "b", **{".homonyms": "keep"})),
        "preserve_false": pack(HTML("a", "b", **{".preserve_empty": False})),
        "check_false": pack(HTML("a", "b", **{".check_assign": False})),
        "err_missing": message(lambda: HTML()),
        "err_list": message(lambda: HTML({"b": 1})),
        "err_named": message(lambda: HTML("a", **{".named": "hello"})),
        "err_ignore": message(lambda: HTML("a", **{".ignore_empty": "nope"})),
        "err_hom": message(lambda: HTML("a", **{".homonyms": "nope"})),
        "err_pre": message(lambda: HTML("a", **{".preserve_empty": "x"})),
        "err_chk": message(lambda: HTML("a", **{".check_assign": "x"})),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}, ensure_ascii=False))
