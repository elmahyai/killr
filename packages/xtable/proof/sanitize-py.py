import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.sanitize import NA, Strings, sanitize

example = Path("/home/ahmed/killr_projects/killr/packages/xtable/docs/output/sanitize-python.txt")

LATEX_NAMES = [
    "Ampersand",
    "Greater than",
    "Less than",
    "Underscore",
    "Percent",
    "Dollar",
    "Backslash",
    "Hash",
    "Caret",
    "Tilde",
    "Left brace",
    "Right brace",
]
HTML_NAMES = ["Ampersand", "Greater than", "Less than"]


def encode_string(value):
    if value is NA:
        return "NA"
    out = ['"']
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def print_named(values, names, width=80):
    formatted = [encode_string(value) for value in values]
    col_w = max(max(len(name) for name in names), max(len(text) for text in formatted))
    n_per = max(1, width // (col_w + 1))
    lines = []
    for start in range(0, len(values), n_per):
        chunk_names = names[start : start + n_per]
        chunk_values = formatted[start : start + n_per]
        lines.append("".join(name.rjust(col_w) + " " for name in chunk_names))
        lines.append("".join(text.rjust(col_w) + " " for text in chunk_values))
    return "\n".join(lines)


latex_in = Strings(
    ["&", ">", ">", "_", "%", "$", "\\", "#", "^", "~", "{", "}"],
    LATEX_NAMES,
)
html_in = Strings(["&", ">", "<"], HTML_NAMES)
printed = print_named(sanitize(latex_in, type="latex"), LATEX_NAMES)
printed += "\n"
printed += print_named(sanitize(html_in, type="html"), HTML_NAMES)
printed += "\n"
example.write_text(printed)

piece = [
    "&",
    ">",
    "<",
    "|",
    "{",
    "}",
    "%",
    "_",
    "#",
    "^",
    "~",
    "$",
    "\\",
    "SANITIZE.BACKSLASH",
    "\\$><|{}%&_#^~",
    "a&b<c>d",
    "&<>&",
    "100%",
    "a_b",
    "",
    NA,
    "NA",
    "café & naïve",
    "a&\nb<c>",
    "xSANITIZE.BACKSLASHy",
    "\\SANITIZE.BACKSLASH",
    "already &amp;",
    "p|q",
    "~^#_",
    "no specials",
    "\\&\\%\\_",
    "a^b",
    "~~~",
]
text = piece * 800
example_latex = Strings(
    ["&", ">", ">", "_", "%", "$", "\\", "#", "^", "~", "{", "}"],
    LATEX_NAMES,
)
example_html = Strings(["&", ">", "<"], HTML_NAMES)
numbers = [
    1e-4,
    1e5,
    10000.0,
    0.00015,
    2e5,
    NA,
    float("nan"),
    float("inf"),
    float("-inf"),
    -0.0,
    1 / 3,
    1e16,
    1e15,
    1e-20,
    0.1,
    10.0,
    0.001,
    1e4,
    123456789012345.0,
    1.23456789012345e-8,
]


def plain(value):
    if value is NA:
        return None
    if isinstance(value, Strings):
        return [plain(item) for item in value]
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def message_of(kind):
    try:
        return sanitize("a", kind)
    except ValueError as exc:
        return [str(exc)]


def one():
    latex_example = sanitize(example_latex, "latex")
    html_example = sanitize(example_html, "html")
    return {
        "latex": sanitize(text, "latex"),
        "html": sanitize(text, "html"),
        "default": sanitize(text),
        "other": sanitize(["a&b<c>d"], "foo"),
        "upper": sanitize(["a&b", "c<d"], "HTML"),
        "example_latex": list(latex_example),
        "example_latex_names": latex_example.names,
        "example_html": list(html_example),
        "example_html_names": html_example.names,
        "numbers": sanitize(numbers),
        "integer": sanitize([100000, 1, NA, -2147483647, 0]),
        "logical": sanitize([True, False, NA]),
        "mixed": sanitize(["a<", 1e5, True, 100000, NA]),
        "empty": sanitize([]),
        "null": sanitize(None),
        "na": sanitize(NA),
        "single": sanitize("a&b"),
        "true_type": sanitize("a&b", True),
        "one_type": sanitize("a&b", "latex"),
        "plain_names": sanitize("a&b").names,
        "err_null": message_of(None),
        "err_na": message_of(NA),
        "err_len": message_of(["latex", "html"]),
        "nan_type": sanitize("a&b", float("nan")),
        "err_empty_type": message_of([]),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
