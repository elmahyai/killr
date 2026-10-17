import json
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/htmltools")

from htmltools.escape import NA, is_na
from htmltools.tag_list import EMPTY, MissingSymbol, Named, Splice, TagList, tagList

example = Path("/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/tagList-python.txt")
manual = tagList(
    {"name": "h1", "children": ["Title"]},
    {"name": "h2", "style": "color: red;", "children": ["Header text"]},
    {"name": "p", "children": ["Text here"]},
)
shown = [
    'tagList(h1("Title"), h2("Header text", style = "color: red;"), p("Text here")) returns class '
    + " ".join(manual.r_class)
    + f", length {len(manual)}."
]
for child in manual:
    shown.append(child["name"] + " " + child["children"][0])
example.write_text("\n".join(shown) + "\n")

SEP = "\x1f"


def join_names(names):
    return SEP.join(names)


def pack_one(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, MissingSymbol):
        return {"type": "symbol", "value": ""}
    if isinstance(value, TagList):
        return pack_tag(value)
    if is_na(value):
        return {"type": "logical", "missing": True}
    if isinstance(value, bool):
        return {"type": "logical", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "double", "value": value}
    if isinstance(value, str):
        return {"type": "character", "value": value}
    if isinstance(value, dict):
        return {
            "type": "list",
            "n": len(value),
            "names": join_names("" if key is None else str(key) for key in value.keys()),
            "items": [pack_one(item) for item in value.values()],
        }
    if isinstance(value, (list, tuple)):
        return {
            "type": "list",
            "n": len(value),
            "names": None,
            "items": [pack_one(item) for item in value],
        }
    raise TypeError(type(value).__name__)


def pack_tag(value):
    return {
        "type": "tagList",
        "class": list(value.r_class),
        "n": len(value),
        "names": join_names(value.names),
        "items": [pack_one(item) for item in value],
    }


def note(caught):
    return "\n---\n".join(str(item.message) for item in caught)


def run(fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            value = fn()
        except ValueError as exc:
            return {"error": str(exc), "value": None, "warnings": note(caught)}
        return {"error": None, "value": pack_tag(value), "warnings": note(caught)}


def one():
    foo = 10.0
    return {
        "empty": run(lambda: tagList()),
        "one": run(lambda: tagList("hi")),
        "two": run(lambda: tagList("one", "two")),
        "nested": run(lambda: tagList("one", tagList("three"))),
        "named": run(lambda: tagList(a=1.0, b="x")),
        "dup": run(lambda: tagList(Named("a", 1.0), Named("a", 2.0))),
        "null": run(lambda: tagList(None)),
        "null_mid": run(lambda: tagList("a", None, "b")),
        "types": run(lambda: tagList(1.0, 2, True, False, NA, None, "a", "")),
        "utf": run(lambda: tagList("caf\u00e9")),
        "list_one": run(lambda: tagList(["one"])),
        "list_named": run(lambda: tagList({"b": 1.0, "c": "x"})),
        "trail": run(lambda: tagList("hi", EMPTY)),
        "trail_preserve": run(lambda: tagList("hi", EMPTY, **{".preserve_empty": True})),
        "ignore_all": run(lambda: tagList(EMPTY, "a", EMPTY, "b", EMPTY, **{".ignore_empty": "all"})),
        "preserve_mid": run(lambda: tagList("a", EMPTY, "b", **{".preserve_empty": True})),
        "preserve_na": run(lambda: tagList("a", EMPTY, "b", **{".preserve_empty": NA, ".ignore_empty": "none"})),
        "preserve_vec": run(lambda: tagList("a", EMPTY, "b", **{".preserve_empty": [True, False], ".ignore_empty": "none"})),
        "splice_named": run(lambda: tagList(Splice([1.0, 2.0], ["a", "b"]), c=3.0)),
        "splice_atomic": run(lambda: tagList("p", Splice(["x", "y"]), "z")),
        "splice_null": run(lambda: tagList(Splice(None), "z")),
        "splice_empty": run(lambda: tagList(Splice([]), "z")),
        "splice_tag": run(lambda: tagList(Splice(tagList(a="a", b="b")), "c")),
        "hom_first": run(lambda: tagList(1.0, Named("a", 2.0), 1.0, Named("a", 3.0), **{".homonyms": "first"})),
        "hom_last": run(lambda: tagList(1.0, Named("a", 2.0), 1.0, Named("a", 3.0), **{".homonyms": "last"})),
        "hom_keep": run(lambda: tagList(Named("a", 1.0), Named("a", 2.0), **{".homonyms": "keep"})),
        "hom_splice_last": run(lambda: tagList(Named("a", 1.0), Splice([9.0, 8.0], ["a", "b"]), **{".homonyms": "last"})),
        "named_expr": run(lambda: tagList(1.0 + 2.0, foo, "x", 2, True, None, 1e-4, **{".named": True})),
        "named_splice": run(lambda: tagList(Splice(["x", 2.5, 10, True, None]), **{".named": True})),
        "named_null": run(lambda: tagList("a", **{".named": None})),
        "named_dup": run(lambda: tagList(1.0, 1.0, **{".named": True, ".homonyms": "error"})),
        "big": run(lambda: tagList(*[0.5 * i for i in range(1, 2001)], a="end")),
        "assign_true": run(lambda: tagList((assigned := 1.0), **{".check_assign": True})),
        "assign_two": run(lambda: tagList((a := 1.0), (b := 2.0), **{".check_assign": True})),
        "assign_false": run(lambda: tagList((c := 1.0), **{".check_assign": False})),
        "assign_default": run(lambda: tagList((d := 1.0))),
        "assign_na": run(lambda: tagList((q := 1.0), **{".check_assign": NA})),
        "err_only_empty": run(lambda: tagList(EMPTY)),
        "err_two_trail": run(lambda: tagList("a", EMPTY, EMPTY)),
        "err_lead": run(lambda: tagList(EMPTY, "one", EMPTY)),
        "err_mid": run(lambda: tagList("a", EMPTY, "b")),
        "err_splice_mid": run(lambda: tagList(Splice([1.0, 2.0]), EMPTY, "b")),
        "err_splice_trail": run(lambda: tagList("a", Splice([1.0]), EMPTY, EMPTY)),
        "err_hom_nope": run(lambda: tagList(a=1.0, **{".homonyms": "nope"})),
        "err_hom_f": run(lambda: tagList(a=1.0, **{".homonyms": "f"})),
        "err_ignore_nope": run(lambda: tagList(**{".ignore_empty": "nope"})),
        "err_ignore_t": run(lambda: tagList(**{".ignore_empty": "t"})),
        "err_ignore_vec": run(lambda: tagList(**{".ignore_empty": ["all", "none"]})),
        "err_named_hello": run(lambda: tagList(**{".named": "hello"})),
        "err_named_na": run(lambda: tagList(**{".named": NA})),
        "err_preserve_chr": run(lambda: tagList(**{".preserve_empty": "x"})),
        "err_preserve_null": run(lambda: tagList(**{".preserve_empty": None})),
        "err_preserve_int": run(lambda: tagList(**{".preserve_empty": 1})),
        "err_preserve_dbl": run(lambda: tagList(**{".preserve_empty": 1.0})),
        "err_check_chr": run(lambda: tagList(**{".check_assign": "x"})),
        "err_hom_dup": run(lambda: tagList(Named("a", 1.0), Named("a", 2.0), **{".homonyms": "error"})),
        "err_hom_three": run(lambda: tagList(Named("a", 1.0), Named("a", 2.0), Named("a", 3.0), **{".homonyms": "error"})),
        "err_hom_two": run(lambda: tagList(Named("a", 1.0), Named("b", 2.0), Named("a", 3.0), Named("b", 4.0), **{".homonyms": "error"})),
        "err_preserve_false": run(lambda: tagList("a", EMPTY, "b", **{".preserve_empty": [False, True], ".ignore_empty": "none"})),
        "err_hom_drop": run(lambda: tagList(Named("a", 1.0), EMPTY, Named("a", 2.0), **{".ignore_empty": "all", ".homonyms": "error"})),
        "err_hom_splice": run(lambda: tagList(Named("a", 1.0), Splice([2.0], ["a"]), **{".homonyms": "error"})),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
