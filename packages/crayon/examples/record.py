"""Time each crayon export against R and write the translation record."""

from __future__ import annotations

import json
import statistics
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "proof"
DOCS = ROOT / "docs"
OUT = DOCS / "output"

R_HELPER = r"""
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(crayon))
options(crayon.enabled = TRUE, width = 80)
json_str <- function(s) {
  if (length(s) == 0 || is.na(s)) return("null")
  s <- enc2utf8(as.character(s))
  bytes <- as.integer(charToRaw(s))
  parts <- character(length(bytes))
  for (i in seq_along(bytes)) {
    b <- bytes[[i]]
    parts[[i]] <- if (b == 34) paste0("\\", '"')
      else if (b == 92) paste0("\\", "\\\\")
      else if (b == 10) paste0("\\", "n")
      else if (b == 13) paste0("\\", "r")
      else if (b == 9) paste0("\\", "t")
      else if (b < 32 || b == 127) sprintf("\\u%04x", b)
      else intToUtf8(b)
  }
  paste0('"', paste(parts, collapse = ""), '"')
}
json_val <- function(x) {
  if (is.null(x)) return("null")
  if (is.list(x)) return(paste0("[", paste(vapply(x, json_val, ""), collapse = ","), "]"))
  if (is.logical(x) && length(x) == 1) return(if (isTRUE(x)) "true" else "false")
  if (is.numeric(x) && length(x) == 1) return(sprintf("%.17g", x))
  if (length(x) > 1) return(paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]"))
  if (length(x) == 0) return("[]")
  json_str(x)
}
"""

PY_HEADER = """import json
import statistics
import time

from crayon import *
"""


def _run(argv: list[str], script: str) -> str:
    completed = subprocess.run(argv, input=script, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    return completed.stdout


def _r(script: str) -> str:
    return _run(["Rscript", "-"], script)


def _py(script: str) -> str:
    return _run(
        ["/home/ahmed/killr_projects/killr/.venv/bin/python", "-"],
        "import sys\nsys.path.insert(0, r'%s')\n" % ROOT + script,
    )


def _same(left, right) -> float:
    if left == right:
        return 0.0
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    raise AssertionError(f"mismatch\nR: {left!r}\nPY: {right!r}")


def check(name: str, r_body: str, py_body: str, case: str) -> dict:
    r_script = (
        R_HELPER
        + "one <- function() {\n"
        + textwrap.indent(r_body.strip(), "  ")
        + "\n}\n"
        + "value <- one()\n"
        + "elapsed <- numeric(20)\n"
        + "for (i in seq_len(20)) {\n"
        + "  t0 <- as.numeric(Sys.time())\n"
        + "  one()\n"
        + "  elapsed[[i]] <- as.numeric(Sys.time()) - t0\n"
        + "}\n"
        + "cat(sprintf('{\"value\":%s,\"median_ms\":%.17g}\\n', json_val(value), median(elapsed) * 1000))\n"
    )
    py_script = (
        PY_HEADER
        + 'options(**{"crayon.enabled": True, "width": 80})\n\n'
        + "def one():\n"
        + textwrap.indent(py_body.strip(), "    ")
        + "\n\nvalue = one()\n"
        + "elapsed = []\n"
        + "for _ in range(20):\n"
        + "    started = time.perf_counter()\n"
        + "    one()\n"
        + "    elapsed.append((time.perf_counter() - started) * 1000)\n"
        + 'print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))\n'
    )
    r_path = PROOF / f"{name}-r.R"
    py_path = PROOF / f"{name}-py.py"
    r_path.write_text(r_script)
    py_path.write_text(py_script)
    r_out = json.loads(_r(r_script))
    py_out = json.loads(_py(py_script))
    diff = _same(r_out["value"], py_out["value"])
    py_ms = py_out["median_ms"] or 1e-9
    print(f"ok {name} r={r_out['median_ms']:.4f} py={py_out['median_ms']:.4f}")
    return {
        "case": case,
        "r_ms": r_out["median_ms"],
        "translated_ms": py_out["median_ms"],
        "speedup": r_out["median_ms"] / py_ms,
        "matches": True,
        "max_abs_diff": diff,
        "tolerance": 1e-8,
        "proof": {"r": r_script, "python": py_script},
    }


def capture(name: str, r_src: str, py_src: str) -> None:
    r_script = (
        '.libPaths(c(path.expand("~/R/library"), .libPaths()))\n'
        "suppressPackageStartupMessages(library(crayon))\n"
        "options(crayon.enabled = TRUE, width = 80)\n"
        + r_src
    )
    py_script = PY_HEADER + 'options(**{"crayon.enabled": True, "width": 80})\n' + py_src
    r_text = _r(r_script)
    py_text = _py(py_script)
    if not r_text.endswith("\n"):
        r_text += "\n"
    if not py_text.endswith("\n"):
        py_text += "\n"
    (OUT / f"{name}-r.txt").write_text(r_text)
    (OUT / f"{name}-python.txt").write_text(py_text)
    if r_text != py_text:
        raise AssertionError(f"example {name}\nR:\n{r_text!r}\nPY:\n{py_text!r}")


def _args(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"name": name, "text": text} for name, text in pairs]


def _doc(name, title, description, usage, arguments, details, value, example, py_usage, py_arguments, py_details, py_value, py_example, py_description=None):
    return {
        "name": name,
        "title": title,
        "origin": {
            "description": description,
            "usage": usage,
            "arguments": arguments,
            "details": details,
            "value": value,
            "example": example,
            "output": f"output/{name}-r.txt",
        },
        "translation": {
            "description": py_description or description,
            "usage": py_usage,
            "arguments": py_arguments,
            "details": py_details,
            "value": py_value,
            "example": py_example,
            "output": f"output/{name}-python.txt",
        },
    }


STYLE_BLURB = {
    "reset": "Clear every active style.",
    "bold": "Bold text. The close code is 22.",
    "blurred": "Dim text. crayon calls this blurred so it does not mask dim() from another package.",
    "italic": "Italic text. Not every terminal draws it.",
    "underline": "Underlined text.",
    "inverse": "Swap the foreground and the background.",
    "hidden": "Hide the text.",
    "strikethrough": "Strike through the text. Not every terminal draws it.",
    "black": "Black foreground.",
    "red": "Red foreground.",
    "green": "Green foreground.",
    "yellow": "Yellow foreground.",
    "blue": "Blue foreground.",
    "magenta": "Magenta foreground.",
    "cyan": "Cyan foreground.",
    "white": "White foreground.",
    "silver": "Bright black foreground. crayon calls this silver so it does not mask gray().",
    "bgBlack": "Black background.",
    "bgRed": "Red background.",
    "bgGreen": "Green background.",
    "bgYellow": "Yellow background.",
    "bgBlue": "Blue background.",
    "bgMagenta": "Magenta background.",
    "bgCyan": "Cyan background.",
    "bgWhite": "White background.",
}


def style_spec(name: str) -> dict:
    blurb = STYLE_BLURB[name]
    example_r = f'cat({name}("crayon"), "\\n", sep="")'
    example_py = f'print({name}("crayon"))'
    return {
        "name": name,
        "python": f"crayon.{name}",
        "done": blurb,
        "case": f'{name}("crayon") with crayon.enabled TRUE',
        "r_body": f'{name}("crayon")',
        "py_body": f'return {name}("crayon")',
        "example_r": example_r,
        "example_py": example_py,
        "doc": _doc(
            name,
            name,
            blurb,
            f"{name}(...)",
            _args(("...", "Strings to style. They are pasted with a space.")),
            "With crayon.enabled TRUE, or on a color terminal, the string is wrapped in the style's open and close codes. A close code already inside the text is replaced by the open code, so an inner style hands control back to this one. With one color, the text is returned unchanged. Several strings of equal length, or length 1, are pasted with a space and styled element by element.",
            "The styled character vector.",
            example_r,
            f"{name}(*text, sep=' ')",
            _args(("text", "Strings or character vectors. A str is one element."), ("sep", "Separator used when more than one argument is pasted. The default is a space.")),
            "Call the style. Attribute access combines another style from styles(), so red.bold is red $ bold. Unary minus copies the style and, when color is on, uses the close code as the open code. options(crayon.enabled=True) turns color on in a non-interactive session.",
            "The styled string, or a list of strings when the pasted vector is longer than one.",
            example_py,
        ),
    }


def specs() -> list[dict]:
    rows = [
        style_spec(name)
        for name in [
            "reset", "bold", "blurred", "italic", "underline", "inverse", "hidden", "strikethrough",
            "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "silver",
            "bgBlack", "bgRed", "bgGreen", "bgYellow", "bgBlue", "bgMagenta", "bgCyan", "bgWhite",
        ]
    ]
    rows.extend([
        {
            "name": "%+%",
            "python": "crayon.concat",
            "done": "Paste two character vectors without a separator. An empty argument stays empty.",
            "case": '"foo" %+% "bar"',
            "r_body": '"foo" %+% "bar"',
            "py_body": 'return concat("foo", "bar")',
            "example_r": 'cat("foo" %+% "bar", "\\n", sep="")\ncat(paste(letters[1:10] %+% chr(1:10), collapse=" "), "\\n", sep="")\ncat(if (length(character() %+% "*") == 0) "character(0)\\n")',
            "example_py": 'print(concat("foo", "bar"))\nprint(" ".join(concat(list("abcdefghij"), [str(i) for i in range(1, 11)])))\nprint("character(0)" if concat([], "*") == [] else concat([], "*"))',
            "doc": _doc(
                "%+%",
                "Concatenate character vectors",
                "Paste two character vectors with no separator.",
                "lhs %+% rhs",
                _args(("lhs", "Left-hand character vector."), ("rhs", "Right-hand character vector.")),
                "The lengths must match, or one of them must be 1. If either argument has length 0, the result has length 0. A length-1 argument is recycled.",
                "The concatenated character vector.",
                'cat("foo" %+% "bar", "\\n", sep="")\ncat(paste(letters[1:10] %+% chr(1:10), collapse=" "), "\\n", sep="")\ncat(if (length(character() %+% "*") == 0) "character(0)\\n")',
                "concat(lhs, rhs)",
                _args(("lhs", "A str, or a list of strings. A str has length 1."), ("rhs", "A str, or a list of strings.")),
                "This is %+%. A str is not iterated character by character. An empty list on either side returns an empty list.",
                "The concatenated string, or a list of strings.",
                'print(concat("foo", "bar"))\nprint(" ".join(concat(list("abcdefghij"), [str(i) for i in range(1, 11)])))\nprint("character(0)" if concat([], "*") == [] else concat([], "*"))',
            ),
        },
        {
            "name": "chr",
            "python": "crayon.chr",
            "done": "Coerce to character. A style function becomes its open code.",
            "case": "chr(1:10)",
            "r_body": "chr(1:10)",
            "py_body": "return chr(list(range(1, 11)))",
            "example_r": 'cat(paste(chr(1:10), collapse=" "), "\\n", sep="")\ncat(chr(red), "\\n", sep="")',
            "example_py": 'print(" ".join(chr(list(range(1, 11)))))\nprint(chr(red))',
            "doc": _doc(
                "chr",
                "Convert to character",
                "Coerce a value with as.character. A crayon style becomes its opening ANSI sequence.",
                "chr(x, ...)",
                _args(("x", "Object to coerce."), ("...", "Further arguments, ignored for a style.")),
                "For a style function this is start(x). For anything else it is as.character.",
                "A character vector.",
                'cat(paste(chr(1:10), collapse=" "), "\\n", sep="")\ncat(chr(red), "\\n", sep="")',
                "chr(x)",
                _args(("x", "A style, a str, a number, or a list.")),
                "A style returns start(x). Numbers use their decimal spelling, and a whole number has no decimal point. A list comes back as a list of strings.",
                "A string, or a list of strings.",
                'print(" ".join(chr(list(range(1, 11)))))\nprint(chr(red))',
            ),
        },
        {
            "name": "combine_styles",
            "python": "crayon.combine_styles",
            "done": "Build one style function. The right-most style is applied first.",
            "case": 'combine_styles(bold, red, bgCyan)("Warning!")',
            "r_body": 'combine_styles(bold, red, bgCyan)("Warning!")',
            "py_body": 'return combine_styles(bold, red, bgCyan)("Warning!")',
            "example_r": 'alert <- bold $ red $ bgCyan\ncat(alert("Warning!"), "\\n", sep="")',
            "example_py": 'alert = bold.red.bgCyan\nprint(alert("Warning!"))',
            "doc": _doc(
                "combine_styles",
                "Combine two or more ANSI styles",
                "Combine styles into one function. They are applied from right to left.",
                "combine_styles(...)\ncrayon $ style",
                _args(("...", "Style functions or names from styles()."), ("crayon", "A style function, on the left of $."), ("style", "A name in styles(), on the right of $.")),
                "Two foreground colors, or two background colors, fight: the outer one wins because it is applied later. $ looks the name up in styles() and appends that style. The original style function is left unchanged.",
                "The combined style function.",
                'alert <- bold $ red $ bgCyan\ncat(alert("Warning!"), "\\n", sep="")',
                "combine_styles(*styles)\nstyle.name",
                _args(("styles", "Style functions or names."), ("name", "An attribute, the style name used on the right of $.")),
                "bold.red.bgCyan is bold $ red $ bgCyan. The right-most style is the inner one. Combining does not change the style it started from.",
                "The combined style function.",
                'alert = bold.red.bgCyan\nprint(alert("Warning!"))',
            ),
        },
        {
            "name": "make_style",
            "python": "crayon.make_style",
            "done": "Bake a style from a builtin name, an R color, or RGB. The color count is read when the style is created.",
            "case": 'make_style("pink", colors=256)("x")',
            "r_body": 'make_style("pink", colors = 256)("x")',
            "py_body": 'return make_style("pink", colors=256)("x")',
            "example_r": 'pink <- make_style("pink", colors = 256)\ncat(pink("pink"), "\\n", sep="")\ncat(make_style("yellow3", colors = 8)("eight"), "\\n", sep="")',
            "example_py": 'pink = make_style("pink", colors=256)\nprint(pink("pink"))\nprint(make_style("yellow3", colors=8)("eight"))',
            "doc": _doc(
                "make_style",
                "Create an ANSI color style",
                "Create a style function from a builtin name, an R color name, a #rrggbb string, or RGB channels.",
                "make_style(..., bg = FALSE, grey = FALSE, colors = num_colors())",
                _args(
                    ("...", "One style. A name creates an entry in styles() as well as the function."),
                    ("bg", "Apply the color to the background."),
                    ("grey", "Use the 24-step ANSI grey ramp. Ignored when fewer than 256 colors are requested."),
                    ("colors", "How many colors to bake. Below 256, the nearest of the eight ANSI colors is used."),
                ),
                "The open and close codes are chosen when make_style runs. Calling the function later only wraps text, and it wraps only when num_ansi_colors() is greater than 1. An 8-digit hex color is accepted and its alpha byte is ignored. A builtin name such as red stays that builtin; with bg TRUE, red becomes bgRed.",
                "A style function.",
                'pink <- make_style("pink", colors = 256)\ncat(pink("pink"), "\\n", sep="")\ncat(make_style("yellow3", colors = 8)("eight"), "\\n", sep="")',
                "make_style(spec, bg=False, grey=False, colors=None, **named)",
                _args(
                    ("spec", "A builtin name, an R color name, #rrggbb, or three or four channel numbers."),
                    ("bg", "Apply the color to the background."),
                    ("grey", "Use the ANSI grey ramp when at least 256 colors are requested."),
                    ("colors", "Color count baked into the style. None uses num_colors()."),
                    ("named", "One named argument also stores the style under that name."),
                ),
                "A sequence of three or four numbers stands in for the one-column RGB matrix. The baked codes do not change if num_colors() changes later. cli.palette remaps a builtin color at call time when at least 256 colors are enabled.",
                "A style function.",
                'pink = make_style("pink", colors=256)\nprint(pink("pink"))\nprint(make_style("yellow3", colors=8)("eight"))',
            ),
        },
        {
            "name": "style",
            "python": "crayon.style",
            "done": "Apply a foreground style and then a background style.",
            "case": 'style("foobar", "bold")',
            "r_body": 'style("foobar", "bold")',
            "py_body": 'return style("foobar", "bold")',
            "example_r": 'cat(style("foobar", "bold"), "\\n", sep="")\ncat(style("foobar", bold), "\\n", sep="")',
            "example_py": 'print(style("foobar", "bold"))\nprint(style("foobar", bold))',
            "doc": _doc(
                "style",
                "Add style to a string",
                "Style a string with a foreground and an optional background.",
                "style(string, as = NULL, bg = NULL)",
                _args(
                    ("string", "Character vector to style."),
                    ("as", "A style function, a name in styles(), or a value make_style() accepts."),
                    ("bg", "A background style function, or a value passed to make_style(..., bg = TRUE)."),
                ),
                "NULL means no change. A name in styles() uses that style. Anything else is given to make_style. The background is applied first, then the foreground.",
                "The styled character vector.",
                'cat(style("foobar", "bold"), "\\n", sep="")\ncat(style("foobar", bold), "\\n", sep="")',
                "style(string, as_=None, bg=None)",
                _args(
                    ("string", "A string or a list of strings."),
                    ("as_", "R's argument as. A style, a name, or a make_style() specification. The second positional argument is the same thing."),
                    ("bg", "Background style. A specification is passed to make_style with bg=True."),
                ),
                "as is a Python keyword, so the parameter is as_. style(text, \"bold\") still matches the R call. A missing side is left unchanged.",
                "The styled string or list.",
                'print(style("foobar", "bold"))\nprint(style("foobar", bold))',
            ),
        },
        {
            "name": "styles",
            "python": "crayon.styles",
            "done": "List the builtin styles and any styles make_style() has named.",
            "case": "names(styles())",
            "r_body": "names(styles())",
            "py_body": "return list(styles())",
            "example_r": 'cat(paste(names(styles()), collapse=", "), "\\n", sep="")',
            "example_py": 'print(", ".join(styles()))',
            "doc": _doc(
                "styles",
                "ANSI escape sequences of crayon styles",
                "The open and close sequences of every named style.",
                "styles()",
                [],
                "Builtin styles are entered when the package loads. make_style(name = ...) adds a name, and drop_style() removes one. Each element has open and close, and a color style also has a palette index.",
                "A named list of open and close sequences.",
                'cat(paste(names(styles()), collapse=", "), "\\n", sep="")',
                "styles()",
                [],
                "A dict in the builtin order, then any names added later. Each value has open, close, and palette. palette is None for bold, italic, and the other non-color styles.",
                "A dict of style records.",
                'print(", ".join(styles()))',
            ),
        },
        {
            "name": "drop_style",
            "python": "crayon.drop_style",
            "done": "Remove a name from styles(). A missing name is ignored.",
            "case": 'drop_style("new_style") after make_style(new_style="maroon")',
            "r_body": 'invisible(make_style(new_style = "maroon", bg = TRUE))\ndrop_style("new_style")\n"new_style" %in% names(styles())',
            "py_body": 'make_style(**{"new_style": "maroon"}, bg=True)\ndrop_style("new_style")\nreturn "new_style" in styles()',
            "example_r": 'invisible(make_style(new_style = "maroon", bg = TRUE))\ncat(style("I am maroon", "new_style"), "\\n", sep="")\ndrop_style("new_style")\ncat("new_style" %in% names(styles()), "\\n", sep="")',
            "example_py": 'make_style(**{"new_style": "maroon"}, bg=True)\nprint(style("I am maroon", "new_style"))\ndrop_style("new_style")\nprint("TRUE" if "new_style" in styles() else "FALSE")',
            "doc": _doc(
                "drop_style",
                "Remove a style",
                "Remove a name from styles(). A name that is not there is ignored.",
                "drop_style(style)",
                _args(("style", "Name to remove.")),
                "The style functions created at load, such as red(), keep the codes they were built with. Dropping the name only changes styles() and the $ lookup.",
                "NULL, invisibly.",
                'invisible(make_style(new_style = "maroon", bg = TRUE))\ncat(style("I am maroon", "new_style"), "\\n", sep="")\ndrop_style("new_style")\ncat("new_style" %in% names(styles()), "\\n", sep="")',
                "drop_style(style)",
                _args(("style", "Name to remove.")),
                "Returns None. red itself is unchanged if the name red is removed; later attribute lookup of .red fails because it reads styles().",
                "None.",
                'make_style(**{"new_style": "maroon"}, bg=True)\nprint(style("I am maroon", "new_style"))\ndrop_style("new_style")\nprint("TRUE" if "new_style" in styles() else "FALSE")',
                py_description="Remove a name from styles(). A missing name is ignored.",
            ),
        },
        {
            "name": "start",
            "python": "crayon.start",
            "done": "The opening ANSI sequence of a style, or empty when color is off.",
            "case": "start(red) with crayon.enabled TRUE",
            "r_body": "start(red)",
            "py_body": "return start(red)",
            "example_r": 'cat(start(red), "name", finish(red), "\\n", sep="")',
            "example_py": 'print(start(red) + "name" + finish(red))',
            "doc": _doc(
                "start",
                "Switch on or off a style",
                "The opening sequence of a style. finish() is the closing sequence, in reverse order.",
                "start(x, ...)\nfinish(x, ...)",
                _args(("x", "A style function."), ("...", "Ignored.")),
                "start is the crayon method of the stats generic. It is used when later output should stay in the style, for example a prompt. Both return an empty string when num_ansi_colors() is 1.",
                "A length-1 character string.",
                'cat(start(red), "name", finish(red), "\\n", sep="")',
                "start(style)\nfinish(style)",
                _args(("style", "A style function.")),
                "There is no stats generic here. start() and finish() take a crayon style. The open codes are concatenated in order; the close codes are concatenated from the inside out.",
                "The opening or closing sequence, or an empty string when color is off.",
                'print(start(red) + "name" + finish(red))',
            ),
        },
        {
            "name": "finish",
            "python": "crayon.finish",
            "done": "The closing ANSI sequence of a style, innermost last.",
            "case": "finish(red) with crayon.enabled TRUE",
            "r_body": "finish(red)",
            "py_body": "return finish(red)",
            "example_r": 'cat(finish(bold $ red), "\\n", sep="")',
            "example_py": 'print(finish(bold.red))',
            "doc": _doc(
                "finish",
                "Switch off a style",
                "The closing sequence of a style, from the last combined style back to the first.",
                "finish(x, ...)",
                _args(("x", "A style function."), ("...", "Ignored.")),
                "Dispatches on the class. The crayon method reverses the close codes. An empty string is returned when color is off.",
                "A length-1 character string.",
                'cat(finish(bold $ red), "\\n", sep="")',
                "finish(style)",
                _args(("style", "A style function.")),
                "The close code of each combined style, last style first.",
                "The closing sequence, or an empty string when color is off.",
                'print(finish(bold.red))',
            ),
        },
        {
            "name": "has_color",
            "python": "crayon.has_color",
            "done": "TRUE when num_ansi_colors() is greater than 1.",
            "case": "has_color() with crayon.enabled TRUE",
            "r_body": "has_color()",
            "py_body": "return has_color()",
            "example_r": 'cat(has_color(), "\\n", sep="")',
            "example_py": 'print("TRUE" if has_color() else "FALSE")',
            "doc": _doc(
                "has_color",
                "Does the current R session support ANSI colors?",
                "TRUE when the session will emit ANSI color.",
                "has_color()",
                [],
                "This is num_ansi_colors() > 1. crayon.enabled TRUE forces that count to 8 unless crayon.colors or cli.num_colors says otherwise.",
                "TRUE or FALSE.",
                'cat(has_color(), "\\n", sep="")',
                "has_color()",
                [],
                "True when num_ansi_colors() is greater than 1. A non-interactive process with no option set reports False, matching Rscript.",
                "True or False.",
                'print("TRUE" if has_color() else "FALSE")',
            ),
        },
        {
            "name": "num_colors",
            "python": "crayon.num_colors",
            "done": "crayon.colors if it is set, otherwise num_ansi_colors().",
            "case": "num_colors() with crayon.enabled TRUE",
            "r_body": "num_colors()",
            "py_body": "return num_colors()",
            "example_r": 'cat(num_colors(), "\\n", sep="")',
            "example_py": "print(num_colors())",
            "doc": _doc(
                "num_colors",
                "Number of colors the terminal supports",
                "How many colors crayon should bake. crayon.colors wins when it is set.",
                "num_colors(forget = FALSE)",
                _args(("forget", "Ignored. Kept for old callers.")),
                "If crayon.colors is set, that integer is returned even when crayon.enabled is unset. Otherwise this is num_ansi_colors().",
                "An integer color count.",
                'cat(num_colors(), "\\n", sep="")',
                "num_colors(forget=False)",
                _args(("forget", "Ignored.")),
                "Set crayon.colors through options(). When it is missing, the result is num_ansi_colors().",
                "An integer.",
                "print(num_colors())",
            ),
        },
        {
            "name": "num_ansi_colors",
            "python": "crayon.num_ansi_colors",
            "done": "Detect the ANSI color count. crayon.enabled TRUE selects 8 unless crayon.colors is set.",
            "case": "num_ansi_colors() with crayon.enabled TRUE",
            "r_body": "num_ansi_colors()",
            "py_body": "return num_ansi_colors()",
            "example_r": 'cat(num_ansi_colors(), "\\n", sep="")',
            "example_py": "print(num_ansi_colors())",
            "doc": _doc(
                "num_ansi_colors",
                "Detect the number of ANSI colors to use",
                "How many ANSI colors the session should use for a stream.",
                'num_ansi_colors(stream = "auto")',
                _args(("stream", '"auto", "stdout", "stderr", or "message". The implementation replaces this with stdout or stderr before the terminal test.')),
                "cli.num_colors and R_CLI_NUM_COLORS win first. crayon.enabled FALSE returns 1. crayon.enabled TRUE returns crayon.colors, or 8. NO_COLOR, knitr, a sink, and a non-terminal stream return 1. A terminal then follows COLORTERM, Emacs, Windows, and tput colors. truecolor is 256^3. The requested stream is not the connection that is tested: outside a REPL the test uses stderr.",
                "An integer.",
                'cat(num_ansi_colors(), "\\n", sep="")',
                'num_ansi_colors(stream="auto")',
                _args(("stream", '"auto", "stdout", "stderr", or "message".')),
                "The same order as crayon. A non-interactive process is not a terminal, so the count is 1 until crayon.enabled, cli.num_colors, or R_CLI_NUM_COLORS is set. There is no R sink; options(crayon.sink_output=1) is the stand-in for an active output sink. Windows 10 build numbers come from the Windows version when the process is on Windows.",
                "An integer.",
                "print(num_ansi_colors())",
            ),
        },
        {
            "name": "has_style",
            "python": "crayon.has_style",
            "done": "TRUE when a string contains an ANSI CSI sequence.",
            "case": 'has_style(red("foobar"))',
            "r_body": 'has_style(red("foobar"))',
            "py_body": 'return has_style(red("foobar"))',
            "example_r": 'cat(has_style("foobar"), " ", has_style(red("foobar")), "\\n", sep="")',
            "example_py": 'print("TRUE" if has_style("foobar") else "FALSE", "TRUE" if has_style(red("foobar")) else "FALSE")',
            "doc": _doc(
                "has_style",
                "Check if a string has some ANSI styling",
                "Whether each string contains an ANSI escape sequence.",
                "has_style(string)",
                _args(("string", "A character vector.")),
                "The test is a CSI or C1 sequence of the form crayon emits. A plain string is FALSE. red() is TRUE only when color is enabled, because otherwise red() does not insert codes.",
                "A logical vector.",
                'cat(has_style("foobar"), " ", has_style(red("foobar")), "\\n", sep="")',
                "has_style(string)",
                _args(("string", "A string or a list of strings.")),
                "A str is one element. The pattern matches ESC [ ... m and the C1 CSI byte.",
                "A bool, or a list of bools.",
                'print("TRUE" if has_style("foobar") else "FALSE", "TRUE" if has_style(red("foobar")) else "FALSE")',
            ),
        },
        {
            "name": "strip_style",
            "python": "crayon.strip_style",
            "done": "Delete ANSI CSI sequences.",
            "case": 'strip_style(red("foobar"))',
            "r_body": 'strip_style(red("foobar"))',
            "py_body": 'return strip_style(red("foobar"))',
            "example_r": 'cat(strip_style(red("foobar")), "\\n", sep="")',
            "example_py": 'print(strip_style(red("foobar")))',
            "doc": _doc(
                "strip_style",
                "Remove ANSI escape sequences from a string",
                "Remove ANSI CSI sequences from each string.",
                "strip_style(string)",
                _args(("string", "The input string.")),
                "Uses the same pattern as has_style. The bytes of the visible text are left as they were.",
                "The string with escape sequences removed.",
                'cat(strip_style(red("foobar")), "\\n", sep="")',
                "strip_style(string)",
                _args(("string", "A string or a list of strings.")),
                "The same CSI pattern as has_style.",
                "The string, or a list of strings, without escape sequences.",
                'print(strip_style(red("foobar")))',
            ),
        },
        {
            "name": "col_nchar",
            "python": "crayon.col_nchar",
            "done": "nchar() of the string after strip_style().",
            "case": 'col_nchar of red / default / green',
            "r_body": 'col_nchar(paste(red("red"), "default", green("green")))',
            "py_body": 'return col_nchar(red("red") + " default " + green("green"))',
            "example_r": 'str <- paste(red("red"), "default", green("green"))\ncat(col_nchar(str), "\\n", sep="")\ncat(nchar(strip_style(str)), "\\n", sep="")',
            "example_py": 'text = red("red") + " default " + green("green")\nprint(col_nchar(text))\nprint(len(strip_style(text)))',
            "doc": _doc(
                "col_nchar",
                "Count number of characters in an ANSI colored string",
                "Count characters after ANSI sequences are removed.",
                "col_nchar(x, ...)",
                _args(("x", "A character vector, possibly styled."), ("...", "Passed to nchar() after the styles are stripped.")),
                "This is nchar(strip_style(x), ...). The ANSI bytes are not part of the count.",
                "An integer vector.",
                'str <- paste(red("red"), "default", green("green"))\ncat(col_nchar(str), "\\n", sep="")\ncat(nchar(strip_style(str)), "\\n", sep="")',
                "col_nchar(x, type='chars')",
                _args(("x", "A string or a list of strings."), ("type", "chars or width use the Python string length. bytes uses the UTF-8 length.")),
                "The count is taken after strip_style. For the ASCII text in the manual, chars and width agree.",
                "An int, or a list of ints.",
                'text = red("red") + " default " + green("green")\nprint(col_nchar(text))\nprint(len(strip_style(text)))',
            ),
        },
        {
            "name": "col_substr",
            "python": "crayon.col_substr",
            "done": "Substring by visible characters, keeping the ANSI codes that cover that span.",
            "case": "col_substr of the red/default/green string, positions 1 through 5",
            "r_body": 'col_substr(paste(red("red"), "default", green("green")), 1, 5)',
            "py_body": 'return col_substr(red("red") + " default " + green("green"), 1, 5)',
            "example_r": 'str <- paste(red("red"), "default", green("green"))\ncat(col_substr(str, 1, 5), "\\n", sep="")\ncat(col_substr(str, 3, 7), "\\n", sep="")',
            "example_py": 'text = red("red") + " default " + green("green")\nprint(col_substr(text, 1, 5))\nprint(col_substr(text, 3, 7))',
            "doc": _doc(
                "col_substr",
                "Substring(s) of an ANSI colored string",
                "substr() that counts visible characters and keeps the surrounding ANSI codes.",
                "col_substr(x, start, stop)",
                _args(
                    ("x", "A character vector, possibly styled."),
                    ("start", "First visible character, recycled to x."),
                    ("stop", "Last visible character, recycled to x."),
                ),
                "Positions follow the string with styles removed. Codes that open before the slice, and codes that close after it, are copied onto the result so the slice keeps its color. A start past the end is empty. Zero and negative starts are treated as 1 by substr. NA in start or stop is an error. An empty x is returned unchanged.",
                "A character vector the same length as x.",
                'str <- paste(red("red"), "default", green("green"))\ncat(col_substr(str, 1, 5), "\\n", sep="")\ncat(col_substr(str, 3, 7), "\\n", sep="")',
                "col_substr(x, start, stop)",
                _args(("x", "A string or a list of strings."), ("start", "First visible character, 1-based."), ("stop", "Last visible character, 1-based.")),
                "Visible positions ignore CSI sequences. A start or stop that is not an integer is an error. A string is one element, so col_substr(\"red\", 1, 2) is the first two characters, not a substring of a list.",
                "The sliced string, or a list when x has more than one element.",
                'text = red("red") + " default " + green("green")\nprint(col_substr(text, 1, 5))\nprint(col_substr(text, 3, 7))',
            ),
        },
        {
            "name": "col_substring",
            "python": "crayon.col_substring",
            "done": "substring() that recycles the text, then calls col_substr.",
            "case": "col_substring of one styled string at two spans",
            "r_body": 'col_substring(paste(red("red"), "default", green("green")), c(1, 3), c(5, 7))',
            "py_body": 'return col_substring(red("red") + " default " + green("green"), [1, 3], [5, 7])',
            "example_r": 'str <- paste(red("red"), "default", green("green"))\ncat(col_substring(str, c(1, 3), c(5, 7)), sep="\\n")',
            "example_py": 'text = red("red") + " default " + green("green")\nprint("\\n".join(col_substring(text, [1, 3], [5, 7])))',
            "doc": _doc(
                "col_substring",
                "Substring(s) of an ANSI colored string",
                "substring() that keeps ANSI styles. The text is recycled to the longer of the index vectors.",
                "col_substring(text, first, last = 1000000L)",
                _args(
                    ("text", "A character vector, possibly styled."),
                    ("first", "Starting indices."),
                    ("last", "Ending indices. The default is 1000000."),
                ),
                "text is repeated with rep_len until it is as long as the longer index. The indices are then passed to col_substr. An empty text stays empty.",
                "A character vector.",
                'str <- paste(red("red"), "default", green("green"))\ncat(col_substring(str, c(1, 3), c(5, 7)), sep="\\n")',
                "col_substring(text, first, last=1000000)",
                _args(("text", "A string or a list of strings."), ("first", "Starting indices."), ("last", "Ending indices.")),
                "A single string is repeated when first or last is longer, the way rep_len repeats a length-1 character vector. The slices then follow col_substr.",
                "A string, or a list of strings.",
                'text = red("red") + " default " + green("green")\nprint("\\n".join(col_substring(text, [1, 3], [5, 7])))',
            ),
        },
        {
            "name": "col_strsplit",
            "python": "crayon.col_strsplit",
            "done": "Split on the visible text and rebuild each piece with col_substring.",
            "case": 'col_strsplit on dashes inside red, green, and underline',
            "r_body": 's <- red("I am red---") %+% green("and I am green-") %+% underline("I underlined")\ncol_strsplit(s, "[-]+")',
            "py_body": 'text = concat(concat(red("I am red---"), green("and I am green-")), underline("I underlined"))\nreturn col_strsplit(text, "[-]+")',
            "example_r": 's <- red("I am red---") %+% green("and I am green-") %+% underline("I underlined")\ncat(col_strsplit(s, "[-]+")[[1]], sep="\\n")',
            "example_py": 'text = concat(concat(red("I am red---"), green("and I am green-")), underline("I underlined"))\nprint("\\n".join(col_strsplit(text, "[-]+")[0]))',
            "doc": _doc(
                "col_strsplit",
                "Split an ANSI colored string",
                "strsplit() that keeps the ANSI style of each piece.",
                "col_strsplit(x, split, ...)",
                _args(
                    ("x", "A character vector, possibly styled."),
                    ("split", "One regular expression, or a literal when fixed is TRUE. An empty split breaks the string into characters."),
                    ("...", "Passed to gregexpr, including fixed and perl."),
                ),
                "The split is searched in the text with styles removed. Empty pieces at the ends are dropped, and an empty split also drops the empty first match. Each remaining span is taken with col_substring, so the pieces stay colored.",
                "A list of character vectors, one per input string.",
                's <- red("I am red---") %+% green("and I am green-") %+% underline("I underlined")\ncat(col_strsplit(s, "[-]+")[[1]], sep="\\n")',
                "col_strsplit(x, split, fixed=False)",
                _args(("x", "A string or a list of strings."), ("split", "One pattern. An empty string splits into characters."), ("fixed", "When True, split is a literal, not a regular expression.")),
                "The search uses Python's regular expressions. The empty-split and end-trimming rules follow crayon. The result is always a list of lists, one list of pieces per input string.",
                "A list of lists of strings.",
                'text = concat(concat(red("I am red---"), green("and I am green-")), underline("I underlined"))\nprint("\\n".join(col_strsplit(text, "[-]+")[0]))',
            ),
        },
        {
            "name": "col_align",
            "python": "crayon.col_align",
            "done": "Pad on the visible width from col_nchar.",
            "case": 'col_align(red("foobar"), 20, "center")',
            "r_body": 'col_align(red("foobar"), 20, "center")',
            "py_body": 'return col_align(red("foobar"), 20, "center")',
            "example_r": 'cat(col_align(red("foobar"), 20, "left"), "\\n", sep="")\ncat(col_align(red("foobar"), 20, "center"), "\\n", sep="")\ncat(col_align(red("foobar"), 20, "right"), "\\n", sep="")',
            "example_py": 'print(col_align(red("foobar"), 20, "left"))\nprint(col_align(red("foobar"), 20, "center"))\nprint(col_align(red("foobar"), 20, "right"))',
            "doc": _doc(
                "col_align",
                "Align an ANSI colored string",
                "Pad a styled string to a width, counting only visible characters.",
                'col_align(text, width = getOption("width"), align = c("left", "center", "right"), type = "width")',
                _args(
                    ("text", "The character vector to align."),
                    ("width", "Field width. The default is the width option."),
                    ("align", '"left", "center", or "right". A unique prefix is enough.'),
                    ("type", "Passed to col_nchar() and from there to nchar()."),
                ),
                "Padding is spaces. A field narrower than the text is returned without extra spaces. Center splits the spare columns with ceiling on the left and floor on the right.",
                "The aligned character vector.",
                'cat(col_align(red("foobar"), 20, "left"), "\\n", sep="")\ncat(col_align(red("foobar"), 20, "center"), "\\n", sep="")\ncat(col_align(red("foobar"), 20, "right"), "\\n", sep="")',
                "col_align(text, width=None, align='left', type='width')",
                _args(
                    ("text", "A string or a list of strings."),
                    ("width", "Field width. None uses the width option, default 80."),
                    ("align", '"left", "center", or "right", or a unique prefix.'),
                    ("type", "Passed to col_nchar."),
                ),
                "Spaces are added around the styled string. The count uses col_nchar, so the ANSI codes do not eat the padding.",
                "The aligned string, or a list.",
                'print(col_align(red("foobar"), 20, "left"))\nprint(col_align(red("foobar"), 20, "center"))\nprint(col_align(red("foobar"), 20, "right"))',
            ),
        },
        {
            "name": "hyperlink",
            "python": "crayon.hyperlink",
            "done": "Wrap text in an OSC 8 link when has_hyperlink() is TRUE.",
            "case": 'hyperlink("R", "https://r-project.org") with crayon.hyperlink TRUE',
            "r_body": 'options(crayon.hyperlink = TRUE)\nhyperlink("R", "https://r-project.org")',
            "py_body": 'options(**{"crayon.hyperlink": True})\nreturn hyperlink("R", "https://r-project.org")',
            "example_r": 'options(crayon.hyperlink = TRUE)\ncat("This is an", hyperlink("R", "https://r-project.org"), "link.\\n")',
            "example_py": 'options(**{"crayon.hyperlink": True})\nprint("This is an", hyperlink("R", "https://r-project.org"), "link.")',
            "doc": _doc(
                "hyperlink",
                "Terminal hyperlinks",
                "Create an OSC 8 terminal hyperlink, when the terminal claims to support one.",
                "hyperlink(text, url)",
                _args(("text", "Text to show."), ("url", "URL to open. text and url are recycled when links are enabled.")),
                "When has_hyperlink() is FALSE the text is returned unchanged. Otherwise the text is wrapped in the OSC 8 open and close sequences.",
                "The text, or the text wrapped as a hyperlink.",
                'options(crayon.hyperlink = TRUE)\ncat("This is an", hyperlink("R", "https://r-project.org"), "link.\\n")',
                "hyperlink(text, url)",
                _args(("text", "Text to show."), ("url", "URL to open.")),
                "A false has_hyperlink() returns the text and does not recycle it against the URL. A true result pastes the OSC 8 wrapper, recycling a length-1 side.",
                "The text, or the wrapped link.",
                'options(**{"crayon.hyperlink": True})\nprint("This is an", hyperlink("R", "https://r-project.org"), "link.")',
            ),
        },
        {
            "name": "has_hyperlink",
            "python": "crayon.has_hyperlink",
            "done": "TRUE when crayon.hyperlink is TRUE. Otherwise a terminal test.",
            "case": "has_hyperlink() with crayon.hyperlink TRUE",
            "r_body": "options(crayon.hyperlink = TRUE)\nhas_hyperlink()",
            "py_body": 'options(**{"crayon.hyperlink": True})\nreturn has_hyperlink()',
            "example_r": 'cat(has_hyperlink(), "\\n", sep="")\noptions(crayon.hyperlink = TRUE)\ncat(has_hyperlink(), "\\n", sep="")',
            "example_py": 'print("TRUE" if has_hyperlink() else "FALSE")\noptions(**{"crayon.hyperlink": True})\nprint("TRUE" if has_hyperlink() else "FALSE")',
            "doc": _doc(
                "has_hyperlink",
                "Does stdout support hyperlinks?",
                "Whether stdout should emit OSC 8 hyperlinks.",
                "has_hyperlink()",
                [],
                "crayon.hyperlink TRUE or FALSE is final. Otherwise a non-terminal is FALSE, Windows is TRUE, CI and TeamCity are FALSE, iTerm from 3.1 is TRUE, and VTE from 0.50.1 is TRUE.",
                "TRUE or FALSE.",
                'cat(has_hyperlink(), "\\n", sep="")\noptions(crayon.hyperlink = TRUE)\ncat(has_hyperlink(), "\\n", sep="")',
                "has_hyperlink()",
                [],
                "options(crayon.hyperlink=True) forces True, and False forces False. With the option unset, a pipe or a captured process is False. iTerm and VTE are read from TERM_PROGRAM and VTE_VERSION.",
                "True or False.",
                'print("TRUE" if has_hyperlink() else "FALSE")\noptions(**{"crayon.hyperlink": True})\nprint("TRUE" if has_hyperlink() else "FALSE")',
            ),
        },
        {
            "name": "show_ansi_colors",
            "python": "crayon.show_ansi_colors",
            "done": "Print the 8-color or 256-color table. The colors argument only picks the table.",
            "case": "show_ansi_colors(8) with width 80",
            "r_body": 'paste(capture.output(show_ansi_colors(8)), collapse = "\\n")',
            "py_body": 'import io, contextlib\nbuf = io.StringIO()\nwith contextlib.redirect_stdout(buf):\n    show_ansi_colors(8)\nreturn buf.getvalue().rstrip("\\n")',
            "example_r": "show_ansi_colors(8)",
            "example_py": "show_ansi_colors(8)",
            "doc": _doc(
                "show_ansi_colors",
                "Show the ANSI color table on the screen",
                "Print a sample of the ANSI colors.",
                "show_ansi_colors(colors = num_colors())",
                _args(("colors", "8 prints the builtin styles. 256 prints the color cube and the grey ramp. Below 8, a short message is printed.")),
                "The argument chooses which table to print. The paints inside the 256-color table still follow num_colors(), so the cube uses 256-color codes only when that count is at least 256. The 8-color table is laid out in columns of the width option.",
                "NULL when fewer than 8 colors were requested. Otherwise the table function, invisibly. The table itself is printed.",
                "show_ansi_colors(8)",
                "show_ansi_colors(colors=None)",
                _args(("colors", "None uses num_colors(). 8 and 256 select the two tables.")),
                "The function prints and returns None. The 8-color layout pads with the same twelve-space field crayon uses, in columns of the width option. The 256-color cube calls style() at the current num_colors(), not at the colors argument.",
                "None. The table is written to stdout.",
                "show_ansi_colors(8)",
            ),
        },
    ])
    return rows


def main() -> None:
    PROOF.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    functions = []
    for spec in specs():
        print("..", spec["name"])
        record = check(spec["name"], spec["r_body"], spec["py_body"], spec["case"])
        capture(spec["name"], spec["example_r"], spec["example_py"])
        (DOCS / f"{spec['name']}.json").write_text(json.dumps(spec["doc"], indent=2) + "\n")
        functions.append({
            "name": spec["name"],
            "translated": True,
            "python": spec["python"],
            "loads": [],
            "uses": [],
            "done": spec["done"],
            "not_done": "",
            "blocked_by": [],
            "assigned": "",
            "check": record,
        })
    translation = {
        "name": "crayon",
        "cran_version": "1.5.3",
        "inventory": "complete",
        "status": "complete",
        "blocked_by": [],
        "crate_claims": [],
        "resume": "All 47 exports are done, including start, the crayon method of the generic. %+% is concat, and $ is attribute access. Color follows crayon.enabled; a non-interactive session stays at one color until that option is set. Styles are baked by make_style. There is no compiled code, so there is no crate.",
        "functions": functions,
    }
    (ROOT / "translation.json").write_text(json.dumps(translation, indent=2) + "\n")
    print(f"wrote {len(functions)} functions")


if __name__ == "__main__":
    main()
