import json
import math
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/htmltools")

from htmltools.dependency import Atom, HtmlDependency, Listing, htmlDependency
from htmltools.escape import NA, _character_double, is_na

example = Path("/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/htmlDependency-python.txt")


def _character_complex(value: complex) -> str:
    real = _character_double(float(value.real))
    imag = float(value.imag)
    if imag < 0.0 or (imag == 0.0 and math.copysign(1.0, imag) < 0.0):
        return real + "-" + _character_double(abs(imag)) + "i"
    return real + "+" + _character_double(imag) + "i"


def fmt_dep(prefix, dep):
    bits = []
    for name, item in zip(dep.src.names, dep.src.items):
        element = item.data[0]
        shown = "NA" if element is NA else element
        bits.append(str(name) + "=" + shown)
    script = "NULL" if dep.script is None else dep.script.data[0]
    style = "NULL" if dep.stylesheet is None else dep.stylesheet.data[0]
    flag = "TRUE" if dep.all_files.data[0] is True else "FALSE"
    return (
        prefix
        + " returns "
        + dep.name.data[0]
        + " "
        + dep.version.data[0]
        + " src="
        + ",".join(bits)
        + " script="
        + script
        + " stylesheet="
        + style
        + " all_files="
        + flag
        + "."
    )


js = htmlDependency(
    "jqueryui",
    "1.11.4",
    {"href": "shared/jqueryui"},
    script="jquery-ui.min.js",
)
css = htmlDependency(
    "font-awesome",
    "4.5.0",
    {"href": "shared/font-awesome"},
    stylesheet="css/font-awesome.min.css",
)
example.write_text(
    fmt_dep(
        'htmlDependency("jqueryui", "1.11.4", c(href = "shared/jqueryui"), script = "jquery-ui.min.js")',
        js,
    )
    + "\n"
    + fmt_dep(
        'htmlDependency("font-awesome", "4.5.0", c(href = "shared/font-awesome"), stylesheet = "css/font-awesome.min.css")',
        css,
    )
    + "\n"
)


def encode_names(names):
    if names is None:
        return None
    encoded = []
    for name in names:
        if is_na(name):
            encoded.append({"na": True})
        else:
            encoded.append(name)
    return encoded


def encode_el(mode, element):
    if element is NA:
        return {"na": True}
    if mode == "double":
        if math.isnan(element):
            return {"nan": True}
        if math.isinf(element):
            return {"inf": 1 if element > 0.0 else -1}
        return _character_double(element)
    if mode == "complex":
        return _character_complex(element)
    if mode == "logical":
        return True if element else False
    return element


def encode(value):
    if value is None:
        return {"t": "null"}
    if isinstance(value, HtmlDependency):
        fields = (
            ("name", value.name),
            ("version", value.version),
            ("src", value.src),
            ("meta", value.meta),
            ("script", value.script),
            ("stylesheet", value.stylesheet),
            ("head", value.head),
            ("attachment", value.attachment),
            ("package", value.package),
            ("all_files", value.all_files),
        )
        return {
            "t": "list",
            "names": [name for name, _item in fields],
            "items": [encode(item) for _name, item in fields],
            "class": value.r_class,
        }
    if isinstance(value, Listing):
        return {
            "t": "list",
            "names": encode_names(value.names),
            "items": [encode(item) for item in value.items],
        }
    if isinstance(value, Atom):
        return {
            "t": value.mode,
            "names": encode_names(value.names),
            "data": [encode_el(value.mode, element) for element in value.data],
        }
    raise TypeError(type(value).__name__)


class Result:
    def __init__(self, error, warning, value):
        self.error = error
        self.warning = warning
        self.value = value


def run(fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            value = fn()
            error = None
        except ValueError as exc:
            value = None
            error = str(exc)
    warning = [str(item.message) for item in caught]
    return Result(error, warning or None, value)


def encode_result(result):
    if isinstance(result, Result):
        return {
            "error": result.error,
            "warning": result.warning,
            "value": None if result.value is None else encode(result.value),
        }
    if isinstance(result, list):
        return [encode(item) for item in result]
    raise TypeError(type(result).__name__)


def one():
    na_src = [("a", "p"), (NA, "q")]
    space_src = [(" ", "p")]
    return {
        "example_js": run(
            lambda: htmlDependency(
                "jqueryui", "1.11.4", {"href": "shared/jqueryui"}, script="jquery-ui.min.js"
            )
        ),
        "example_css": run(
            lambda: htmlDependency(
                "font-awesome",
                "4.5.0",
                {"href": "shared/font-awesome"},
                stylesheet="css/font-awesome.min.css",
            )
        ),
        "unnamed": run(lambda: htmlDependency("a", "1", "path")),
        "unnamed_vec": run(lambda: htmlDependency("a", "1", ["p", "q"])),
        "href": run(lambda: htmlDependency("a", "1", {"href": "/"})),
        "both": run(lambda: htmlDependency("a", "1", {"file": "p", "href": "u"})),
        "mixed_empty": run(lambda: htmlDependency("a", "1", {"file": "p", "": "u"})),
        "leading_empty": run(lambda: htmlDependency("a", "1", {"": "p", "href": "u"})),
        "custom_name": run(lambda: htmlDependency("a", "1", {"foo": "p"})),
        "list_both": run(
            lambda: htmlDependency("a", "1", {"file": "p", "href": "u", "": "z"})
        ),
        "empty_src": run(lambda: htmlDependency("a", "1", [])),
        "empty_list": run(lambda: htmlDependency("a", "1", {})),
        "null_src": run(lambda: htmlDependency("a", "1", None)),
        "keep_null": run(lambda: htmlDependency("a", "1", {"file": None, "href": "u"})),
        "dup_file": run(lambda: htmlDependency("a", "1", ["a", "b"])),
        "na_logical": run(lambda: htmlDependency("a", "1", NA)),
        "na_href": run(lambda: htmlDependency("a", "1", {"href": NA})),
        "na_character": run(lambda: htmlDependency("a", "1", ["x", NA])),
        "abs_path": run(lambda: htmlDependency("a", "1", "/tmp/x")),
        "empty_path": run(lambda: htmlDependency("a", "1", "")),
        "num_src": run(lambda: htmlDependency("a", "1", [1.0, 2.0])),
        "logical_src": run(lambda: htmlDependency("a", "1", True)),
        "na_name_src": run(lambda: htmlDependency("a", "1", na_src)),
        "space_name": run(lambda: htmlDependency("a", "1", space_src)),
        "ver_num": run(lambda: htmlDependency("a", 1.11, "p")),
        "ver_int": run(lambda: htmlDependency("a", 1, "p")),
        "ver_sci": run(lambda: htmlDependency("a", 1e5, "p")),
        "ver_small": run(lambda: htmlDependency("a", 1e-4, "p")),
        "ver_true": run(lambda: htmlDependency("a", True, "p")),
        "ver_false": run(lambda: htmlDependency("a", False, "p")),
        "ver_nan": run(lambda: htmlDependency("a", float("nan"), "p")),
        "ver_inf": run(lambda: htmlDependency("a", float("inf"), "p")),
        "ver_neginf": run(lambda: htmlDependency("a", float("-inf"), "p")),
        "ver_half": run(lambda: htmlDependency("a", 0.5, "p")),
        "ver_complex": run(lambda: htmlDependency("a", 1 + 2j, "p")),
        "ver_complex_neg": run(lambda: htmlDependency("a", 1 - 2j, "p")),
        "ver_complex_sci": run(lambda: htmlDependency("a", 1 + 1e5j, "p")),
        "ver_complex_small": run(lambda: htmlDependency("a", complex(1e-4, 2), "p")),
        "name_int": run(lambda: htmlDependency(1, "1", "p")),
        "name_dbl": run(lambda: htmlDependency(1.5, "1", "p")),
        "name_true": run(lambda: htmlDependency(True, "1", "p")),
        "name_nan": run(lambda: htmlDependency(float("nan"), "1", "p")),
        "name_inf": run(lambda: htmlDependency(float("inf"), "1", "p")),
        "name_neginf": run(lambda: htmlDependency(float("-inf"), "1", "p")),
        "name_space": run(lambda: htmlDependency("a b", "1", "p")),
        "name_dot": run(lambda: htmlDependency("a.b", "1", "p")),
        "name_dash": run(lambda: htmlDependency("font-awesome", "1", "p")),
        "name_blank": run(lambda: htmlDependency(" ", "1", "p")),
        "name_unicode": run(lambda: htmlDependency("caf\u00e9", "1", "p")),
        "all_false": run(lambda: htmlDependency("a", "1", "p", all_files=False)),
        "all_na": run(lambda: htmlDependency("a", "1", "p", all_files=NA)),
        "all_zero": run(lambda: htmlDependency("a", "1", "p", all_files=0.0)),
        "all_int": run(lambda: htmlDependency("a", "1", "p", all_files=0)),
        "package": run(lambda: htmlDependency("a", "1", "p", package="htmltools")),
        "package_empty": run(lambda: htmlDependency("a", "1", "p", package="")),
        "meta": run(
            lambda: htmlDependency(
                "a", "1", "p", meta={"name": "viewport", "content": "width=device-width"}
            )
        ),
        "meta_empty": run(lambda: htmlDependency("a", "1", "p", meta={})),
        "script_vec": run(lambda: htmlDependency("a", "1", "p", script=["a.js", "b.js"])),
        "script_list": run(
            lambda: htmlDependency(
                "a",
                "1",
                "p",
                script={"src": "a.js", "integrity": "h", "defer": NA},
            )
        ),
        "script_empty": run(lambda: htmlDependency("a", "1", "p", script=[])),
        "head": run(lambda: htmlDependency("a", "1", "p", head="<script>alert(1)</script>")),
        "attachment": run(
            lambda: htmlDependency(
                "a", "1", "p", attachment=[("foo", "a.txt"), ("", "b.txt")]
            )
        ),
        "style_null": run(lambda: htmlDependency("a", "1", "p", stylesheet=None)),
        "err_empty_name": run(lambda: htmlDependency("", "1", "x")),
        "err_slash_name": run(lambda: htmlDependency("a/b", "1", "x")),
        "err_bslash_name": run(lambda: htmlDependency("a\\b", "1", "x")),
        "err_empty_ver": run(lambda: htmlDependency("a", "", "x")),
        "err_slash_ver": run(lambda: htmlDependency("a", "1/2", "x")),
        "err_bslash_ver": run(lambda: htmlDependency("a", "1\\2", "x")),
        "err_two_name": run(lambda: htmlDependency(["a", "b"], "1", "x")),
        "err_two_ver": run(lambda: htmlDependency("a", ["1", "2"], "x")),
        "err_na_name": run(lambda: htmlDependency(NA, "1", "x")),
        "err_na_ver": run(lambda: htmlDependency("a", NA, "x")),
        "err_null_name": run(lambda: htmlDependency(None, "1", "x")),
        "err_null_ver": run(lambda: htmlDependency("a", None, "x")),
        "err_char0_name": run(lambda: htmlDependency([], "1", "x")),
        "err_char0_ver": run(lambda: htmlDependency("a", [], "x")),
        "err_missing": run(lambda: htmlDependency()),
        "err_missing_ver": run(lambda: htmlDependency("a")),
        "err_missing_src": run(lambda: htmlDependency("a", "1")),
        "err_missing_name": run(lambda: htmlDependency(version="1", src="p")),
        "ns_abs": run(lambda: htmlDependency("a", "1", "/tmp/x", _namespace=True)),
        "ns_rel": run(lambda: htmlDependency("a", "1", "rel/path", _namespace=True)),
        "ns_url": run(
            lambda: htmlDependency(
                "a", "1", {"href": "http://cdn.example/lib"}, _namespace=True
            )
        ),
        "ns_slashslash": run(
            lambda: htmlDependency("a", "1", "//cdn.example/lib", _namespace=True)
        ),
        "ns_multi": run(
            lambda: htmlDependency(
                "a", "1", {"href": "http://x", "file": "/tmp"}, _namespace=True
            )
        ),
        "ns_na": run(lambda: htmlDependency("a", "1", NA, _namespace=True)),
        "ns_missing": run(lambda: htmlDependency(_namespace=True)),
        "ns_missing_src": run(lambda: htmlDependency("a", "1", _namespace=True)),
        "ns_missing_ver": run(lambda: htmlDependency("a", src="p", _namespace=True)),
        "ns_abs_bad_name": run(lambda: htmlDependency("", "1", "/tmp", _namespace=True)),
        "ns_abs_missing_ver": run(
            lambda: htmlDependency("a", src="/tmp", _namespace=True)
        ),
        "bulk": [
            htmlDependency(
                f"lib{i}",
                f"1.{i}.0",
                {"href": f"shared/lib{i}"},
                script=f"lib{i}.min.js",
                stylesheet="x.css" if i % 2 == 0 else None,
                all_files=(i % 3) != 0,
            )
            for i in range(500)
        ],
    }


def encode_one(raw):
    encoded = {}
    for name, item in raw.items():
        encoded[name] = encode_result(item)
    return encoded


raw = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = encode_one(raw)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}, ensure_ascii=False))
