"""Builtin-theme printers: headings, alerts, lists, and inline markup."""

from __future__ import annotations

import os
import sys

from glue import glue as glue_text

from cli.layout import console_width, rule
from cli.styles import (
    col_blue,
    col_cyan,
    col_green,
    col_grey,
    col_red,
    col_yellow,
    style_bold,
    style_italic,
)
from cli.symbol import symbol
from cli._options import get_option
from cli.num_ansi_colors import num_ansi_colors
from cli.unicode_output import is_utf8_output

_COUNT = 0
_APPS: list = []


def new_uuid() -> str:
    global _COUNT
    _COUNT += 1
    return f"cli-{os.getpid()}-{_COUNT}"


def _write(text: str) -> None:
    sys.stderr.write(text)


def _tick(text: str) -> str:
    if "`" in text:
        return f"`` {text} ``"
    return f"`{text}`"


def _tick_fun(text: str) -> str:
    if "`" in text:
        return f"`` {text} ()``"
    return f"`{text}()`"


def _apply_class(name: str, text: str) -> str:
    if name in ("emph",):
        return style_italic(text)
    if name in ("strong",):
        return style_bold(text)
    if name in ("pkg", "file", "path", "email", "version"):
        return col_blue(text)
    if name in ("field",):
        return col_green(text)
    if name in ("code", "arg", "var", "col", "envvar"):
        return _tick(text)
    if name in ("fn", "fun"):
        return _tick_fun(text)
    if name in ("url",):
        return style_italic(col_blue(f"<{text}>"))
    if name in ("kbd", "key"):
        return col_blue(f"[{text}]")
    if name == "timestamp":
        return col_grey(f"[{text}]")
    if name in ("alert", "alert-start"):
        return f"{symbol['arrow_right']} {text}"
    if name == "alert-success":
        return f"{col_green(symbol['tick'])} {text}"
    if name == "alert-danger":
        return f"{col_red(symbol['cross'])} {text}"
    if name == "alert-warning":
        return f"{col_yellow('!')} {text}"
    if name == "alert-info":
        return f"{col_cyan(symbol['info'])} {text}"
    return text


def format_inline(text="", envir=None, collapse=True, keep_whitespace=True):
    """Format one string with glue and the builtin inline classes."""

    if not isinstance(text, str):
        text = " ".join(str(part) for part in text)
    out = []
    index = 0
    while index < len(text):
        if text[index] == "{":
            depth = 1
            cursor = index + 1
            while cursor < len(text) and depth:
                if text[cursor] == "{":
                    depth += 1
                elif text[cursor] == "}":
                    depth -= 1
                cursor += 1
            body = text[index + 1 : cursor - 1]
            out.append(_brace(body, envir))
            index = cursor
        else:
            nxt = text.find("{", index)
            if nxt < 0:
                nxt = len(text)
            out.append(text[index:nxt])
            index = nxt
    rendered = "".join(out)
    if collapse:
        rendered = rendered.replace("\f", "\n")
    return rendered


def _brace(body: str, envir) -> str:
    stripped = body.lstrip()
    if stripped.startswith("."):
        name, _, rest = stripped[1:].partition(" ")
        inner = format_inline(rest, envir=envir) if rest else ""
        return _apply_class(name, inner)
    if envir is None:
        envir = {}
    value = envir.get(body.strip()) if isinstance(envir, dict) and body.strip() in envir else None
    if value is not None and not isinstance(value, str):
        style = getattr(value, "cli_style", None)
        if style is not None:
            from cli.collapse import ansi_collapse

            last = style.get("vec-last", ", and ")
            sep = style.get("vec-sep", ", ")
            sep2 = style.get("vec-sep2")
            if sep2 is None:
                sep2 = last[1:] if str(last).startswith(",") else last
            return ansi_collapse(list(value), sep=sep, sep2=sep2, last=last) or ""
        if isinstance(value, (list, tuple)):
            from cli.collapse import ansi_collapse

            return ansi_collapse(list(value)) or ""
    try:
        return str(glue_text("{" + body + "}", envir=envir if isinstance(envir, dict) else {}))
    except Exception:
        return "{" + body + "}"


def _bullet_line(kind: str, text: str) -> str:
    rendered = format_inline(text)
    if kind in ("", "noindent", "empty"):
        return rendered
    if kind == " ":
        return f"  {rendered}"
    if kind == "*":
        return f"{col_cyan(symbol['bullet'])} {rendered}"
    if kind == "v":
        return f"{col_green(symbol['tick'])} {rendered}"
    if kind == "x":
        return f"{col_red(symbol['cross'])} {rendered}"
    if kind == "!":
        return f"{col_yellow('!')} {rendered}"
    if kind == "i":
        return f"{col_cyan(symbol['info'])} {rendered}"
    if kind == "->":
        return f"{symbol['arrow_right']} {rendered}"
    if kind == "1":
        return style_bold(rendered)
    return rendered


def _items(text):
    if isinstance(text, dict):
        return list(text.items())
    return [("", item) for item in text]


def cli_bullets(text, id=None, class_=None):
    lines = [_bullet_line(kind, item) for kind, item in _items(text)]
    _write("\n".join(lines) + ("\n" if lines else ""))
    return id or new_uuid()


def cli_bullets_raw(text, id=None, class_=None):
    return cli_bullets(text, id=id)


def format_bullets_raw(text, id=None, class_=None) -> str:
    lines = [_bullet_line(kind, item) for kind, item in _items(text)]
    return "\n".join(lines)


def cli(expr):
    """Run cli calls. Each call already writes its own message."""

    if callable(expr):
        expr()
    return None


def cli_text(*parts, envir=None):
    text = format_inline("".join(parts), envir=envir)
    _write(text + "\n")
    return None


def cli_verbatim(*parts, envir=None):
    text = "".join(parts)
    lines = text.split("\n")
    _write("\n".join(lines) + "\n")
    return None


def cli_h1(text, id=None, class_=None, envir=None):
    label = style_bold(format_inline(text, envir=envir))
    _write("\n" + rule(label, line_col="cyan") + "\n")
    return id or new_uuid()


def cli_h2(text, id=None, class_=None, envir=None):
    label = style_bold(style_bold(format_inline(text, envir=envir)))
    line = symbol["line"]
    _write(f"\n{line}{line} {label} {line}{line}\n\n")
    return id or new_uuid()


def cli_h3(text, id=None, class_=None, envir=None):
    label = format_inline(text, envir=envir)
    line = symbol["line"]
    _write(f"\n{line}{line} {label} \n")
    return id or new_uuid()


def cli_alert(text, id=None, class_=None, envir=None):
    _write(f"{symbol['arrow_right']} {format_inline(text, envir=envir)}\n")
    return id or new_uuid()


def cli_alert_success(text, id=None, class_=None, envir=None):
    _write(f"{col_green(symbol['tick'])} {format_inline(text, envir=envir)}\n")
    return id or new_uuid()


def cli_alert_danger(text, id=None, class_=None, envir=None):
    _write(f"{col_red(symbol['cross'])} {format_inline(text, envir=envir)}\n")
    return id or new_uuid()


def cli_alert_warning(text, id=None, class_=None, envir=None):
    _write(f"{col_yellow('!')} {format_inline(text, envir=envir)}\n")
    return id or new_uuid()


def cli_alert_info(text, id=None, class_=None, envir=None):
    _write(f"{col_cyan(symbol['info'])} {format_inline(text, envir=envir)}\n")
    return id or new_uuid()


def cli_ul(items, id=None, class_=None, envir=None):
    lines = [f"{symbol['bullet']} {format_inline(item, envir=envir)}" for item in items]
    _write("\n".join(lines) + "\n")
    return id or new_uuid()


def cli_ol(items, id=None, class_=None, envir=None):
    lines = [
        f"{index}. {format_inline(item, envir=envir)}"
        for index, item in enumerate(items, start=1)
    ]
    _write("\n".join(lines) + "\n")
    return id or new_uuid()


def cli_li(items, id=None, class_=None, envir=None):
    return cli_ul(items if isinstance(items, (list, tuple)) else [items], id=id, envir=envir)


def cli_dl(items, id=None, class_=None, envir=None):
    lines = []
    pairs = items.items() if isinstance(items, dict) else items
    for key, value in pairs:
        lines.append(f"{format_inline(str(key), envir=envir)}: {format_inline(str(value), envir=envir)}")
    _write("\n".join(lines) + "\n")
    return id or new_uuid()


def cli_rule(left="", center="", right="", id=None, envir=None):
    text = rule(
        format_inline(left, envir=envir),
        format_inline(center, envir=envir),
        format_inline(right, envir=envir),
    )
    _write(text + "\n")
    return id or new_uuid()


def cli_blockquote(quote, citation=None, id=None, class_=None, envir=None):
    body = format_inline(quote, envir=envir)
    left = symbol["dquote_left"]
    right = symbol["dquote_right"]
    _write("\n" + "    " + style_italic(f"{left}{body}{right}") + "\n")
    if citation:
        cite = f"{symbol['em_dash']} {format_inline(citation, envir=envir)}"
        _write("    " + style_bold(style_italic(cite)) + "\n\n")
    return id or new_uuid()


def cli_code(*parts, id=None, class_=None, envir=None):
    from cli.highlight import code_highlight

    text = "\n".join(parts)
    lines = [code_highlight(line) for line in text.split("\n")]
    _write("\n".join(lines) + "\n")
    return None


def cli_div(id=None, class_=None, theme=None):
    return id or new_uuid()


def cli_par(id=None, class_=None):
    return id or new_uuid()


def cli_end(id=None):
    return None


def cli_format_method(expr, theme=None):
    return cli_fmt(expr, strip_newline=False)


def cli_fmt(expr, collapse=False, strip_newline=False):
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        expr() if callable(expr) else None
    text = buf.getvalue()
    text = text.rstrip("\n")
    if strip_newline:
        text = text.rstrip("\n")
    if collapse:
        text = text.replace("\n", " ")
    return text


class _App:
    def __init__(self):
        self.kind = "cliapp"


def start_app(theme=None, output="auto", auto_close=True):
    app = _App()
    _APPS.append(app)
    return app


def stop_app(app=None):
    if _APPS:
        _APPS.pop()
    return None


def default_app():
    return _APPS[-1] if _APPS else None


_BUILTIN = [
    "body", "h1", "h2", "h3", ".alert", ".alert-success", ".alert-danger",
    ".alert-warning", ".alert-info", ".bullets .bullet-empty",
    ".bullets .bullet-space", ".bullets .bullet-v", ".bullets .bullet-x",
    ".bullets .bullet-!", ".bullets .bullet-i", ".bullets .bullet-*",
    ".bullets .bullet->", ".bullets .bullet-1", "par", "ul", "span.dt",
    "span.dd", "ul ul li", "ul ol li", "ul dl li", "ol ul li", "ol ol li",
    "ol dl li", "ol ul li", "ol ol li", "ol dl li", "blockquote",
    "blockquote cite", ".code", ".code.R", "span.emph", "span.strong",
    "span.code", "span.q", "span.pkg", "span.fn", "span.fun", "span.arg",
    "span.kbd", "span.key", "span.file", "span.path", "span.email",
    "span.url", "span.href", "span.help", "span.topic", "span.vignette",
    "span.run", "span.var", "span.col", "span.str", "span.envvar",
    "span.val", "span.field", "span.cls", "span.progress-bar",
    "span.obj_type_friendly", "span.type", "span.or", "span.timestamp",
    "span.bytes", "span.num",
]

_SIMPLE = [
    "h1", "h2", "h3", "par", ".alert-danger", ".alert-warning",
    ".alert-success", ".alert-info", ".alert-start", "span.pkg",
    "span.version", "span.emph", "span.strong", "span.fun", "span.fn",
    "span.arg", "span.kbd", "span.key", "span.file", "span.path",
    "span.email", "span.url", "span.var", "span.envvar", "span.timestamp",
]


def builtin_theme(dark="auto"):
    return list(_BUILTIN)


def simple_theme(dark="auto"):
    return list(_SIMPLE)


def cli_list_themes():
    if not _APPS:
        start_app()
    return [list(_BUILTIN)]


def cli_sitrep() -> dict:
    option = get_option("cli.unicode", None)
    return {
        "cli_unicode_option": option,
        "symbol_charset": "UTF-8" if is_utf8_output() else "ASCII (non UTF-8)",
        "console_utf8": True,
        "latex_active": False,
        "num_colors": num_ansi_colors(),
        "console_width": console_width(),
    }


def _fmt_sitrep(value) -> str:
    if value is None:
        return "NULL"
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return str(value)


def format_sitrep(report=None) -> str:
    report = cli_sitrep() if report is None else report
    names = list(report)
    width = max(len(name) for name in names)
    return "\n".join(
        f"- {name.ljust(width)} : {_fmt_sitrep(report[name])}" for name in names
    )


def cli_format(x, style=None):
    if isinstance(x, str):
        quote = '"'
        if isinstance(style, dict) and style.get("string-quote"):
            quote = style["string-quote"]
        escaped = x.replace("\\", "\\\\").replace(quote, "\\" + quote)
        return quote + escaped + quote
    if isinstance(style, dict) and "digits" in style and isinstance(x, float):
        return round(x, style["digits"])
    return x


class _Vec(list):
    def __init__(self, values, style):
        super().__init__(values)
        self.cli_style = style


def cli_vec(x, style=None):
    return _Vec(list(x), style or {})


def _undo_bold(text: str) -> str:
    return style_bold("") + text


def format_message(message, envir=None) -> str:
    if isinstance(message, str):
        message = {"": message}
    return _undo_bold(format_bullets_raw(message))


def format_warning(message, envir=None) -> str:
    if isinstance(message, str):
        message = {"": message}
    return _undo_bold(format_bullets_raw(message))


def format_error(message, envir=None) -> str:
    return format_warning(message, envir=envir)


def cli_inform(message, envir=None):
    _write(format_message(message, envir=envir) + "\n")
    return None


def cli_warn(message, envir=None):
    import warnings

    warnings.warn(format_warning(message, envir=envir), stacklevel=2)
    return None


def cli_abort(message, envir=None):
    raise RuntimeError(format_error(message, envir=envir))


def cli_output_connection() -> str:
    if get_option("rlib_interactive") is True:
        return "stdout"
    return "stderr"


def cat_print(x, file=""):
    if isinstance(x, str):
        shown = f'[1] "{x}"'
    elif isinstance(x, bool):
        shown = f"[1] {'TRUE' if x else 'FALSE'}"
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        shown = f"[1] {x}"
    else:
        shown = str(x)
    print(shown)
    return x
