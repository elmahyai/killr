"""Style constructors from diffobj.

Slot names are stored with the R dots (``na.sub``, ``word.insert``). The same
value is also available under the snake_case spelling (``na_sub``).
``obj.classes`` is the S4 class vector, nearest class first.
"""

from __future__ import annotations

import inspect
import math
import os
import warnings
from collections.abc import Mapping, Sequence

from crayon import (
    bgBlack,
    black,
    blue,
    col_nchar,
    cyan,
    green,
    has_style,
    make_style,
    red,
    silver,
    strip_style,
    yellow,
)
from crayon._colors import rgb
from diffobj.html import cont_f, div_f, nchar_html, span_f
from diffobj.options import gdo
from diffobj.pager import pager_is_less
from diffobj.webfiles import diffobj_css, diffobj_js

# Names used by the ANSI styles and by callers that strip or measure them.
_CRAYON = (bgBlack, black, has_style, strip_style, col_nchar, rgb)

_MISSING = object()

_PARENTS: dict[str, tuple[str, ...]] = {
    "StyleFunsAnsi": ("StyleFuns",),
    "StyleSummaryHtml": ("StyleSummary",),
    "StyleRaw": ("Style", "Raw"),
    "StyleAnsi": ("StyleRaw", "Ansi"),
    "StyleAnsi8NeutralRgb": ("StyleAnsi", "Neutral", "Rgb"),
    "StyleAnsi8NeutralYb": ("StyleAnsi", "Neutral", "Yb"),
    "StyleAnsi256LightRgb": ("StyleAnsi", "Light", "Rgb"),
    "StyleAnsi256LightYb": ("StyleAnsi", "Light", "Yb"),
    "StyleAnsi256DarkRgb": ("StyleAnsi", "Dark", "Rgb"),
    "StyleAnsi256DarkYb": ("StyleAnsi", "Dark", "Yb"),
    "StyleHtml": ("Style", "Html"),
    "StyleHtmlLightRgb": ("StyleHtml", "Light", "Rgb"),
    "StyleHtmlLightYb": ("StyleHtml", "Light", "Yb"),
    "PagerOff": ("Pager",),
    "PagerSystem": ("Pager",),
    "PagerSystemLess": ("PagerSystem",),
    "PagerBrowser": ("Pager",),
}

STYLE_FUN_SLOTS: tuple[str, ...] = (
    "container",
    "row",
    "line",
    "line.insert",
    "line.delete",
    "line.match",
    "line.guide",
    "line.fill",
    "text",
    "text.insert",
    "text.delete",
    "text.match",
    "text.guide",
    "text.fill",
    "banner",
    "banner.insert",
    "banner.delete",
    "gutter",
    "gutter.insert",
    "gutter.insert.ctd",
    "gutter.delete",
    "gutter.delete.ctd",
    "gutter.match",
    "gutter.match.ctd",
    "gutter.guide",
    "gutter.guide.ctd",
    "gutter.fill",
    "gutter.fill.ctd",
    "gutter.context.sep",
    "gutter.context.sep.ctd",
    "gutter.pad",
    "word.insert",
    "word.delete",
    "context.sep",
    "header",
    "meta",
    "trim",
)

STYLE_TEXT_SLOTS: tuple[str, ...] = (
    "gutter.insert",
    "gutter.insert.ctd",
    "gutter.delete",
    "gutter.delete.ctd",
    "gutter.match",
    "gutter.match.ctd",
    "gutter.guide",
    "gutter.guide.ctd",
    "gutter.fill",
    "gutter.fill.ctd",
    "gutter.context.sep",
    "gutter.context.sep.ctd",
    "gutter.pad",
    "context.sep",
    "pad.col",
    "line.break",
)

STYLE_SUMMARY_SLOTS: tuple[str, ...] = ("container", "body", "map", "detail")

STYLE_SLOTS: tuple[str, ...] = (
    "funs",
    "text",
    "summary",
    "nchar.fun",
    "wrap",
    "pad",
    "finalizer",
    "pager",
    "na.sub",
    "blank.sub",
    "disp.width",
)

HTML_SLOTS: tuple[str, ...] = (
    "css",
    "html.output",
    "escape.html.entities",
    "js",
    "scale",
)

_HTML_OUTPUTS = ("auto", "page", "diff.only", "diff.w.style")

_PAGE = (
    "\n"
    "        <!DOCTYPE html>\n"
    "        <html>\n"
    "          <head>\n"
    "            %s\n"
    "\n"
    "            %%s\n"
    "\n"
    "          </head>\n"
    "          <body>\n"
    "            <div id='diffobj_outer'>\n%%s\n</div>\n"
    "            <script type='text/javascript'>\n%s\n</script>\n"
    "          </body>\n"
    "        </html>"
)

_CHARSET = '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>'


class _LogicalNA:
    def __repr__(self) -> str:
        return "NA"


LOGICAL_NA = _LogicalNA()


def class_vector(name: str) -> tuple[str, ...]:
    """S4 ``is()`` order: the class, then superclasses by distance."""

    result = [name]
    seen = {name}
    frontier = [name]
    while frontier:
        nxt: list[str] = []
        for cls in frontier:
            for parent in _PARENTS.get(cls, ()):
                if parent not in seen:
                    seen.add(parent)
                    result.append(parent)
                    nxt.append(parent)
        frontier = nxt
    return tuple(result)


def inherits(obj: object, name: str) -> bool:
    """Whether ``obj`` is S4 class ``name`` or extends it."""

    classes = getattr(obj, "classes", ())
    if name in classes:
        return True
    if getattr(obj, "kind", None) == name:
        return True
    return type(obj).__name__ == name


class Slots:
    """An S4-style object. Dotted slot names are real attributes."""

    def __init__(self, classes: tuple[str, ...] | list[str], values: Mapping[str, object]):
        object.__setattr__(self, "_values", {})
        object.__setattr__(self, "classes", tuple(classes))
        for key, value in values.items():
            self._write(key, value)

    def _write(self, key: str, value: object) -> None:
        self._values[key] = value
        object.__setattr__(self, key, value)
        snake = key.replace(".", "_")
        if snake != key:
            object.__setattr__(self, snake, value)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "classes" or name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        key = name if name in self._values else name.replace("_", ".")
        if key not in self._values:
            raise AttributeError(f"invalid slot '{name}'")
        self._write(key, value)

    def __repr__(self) -> str:
        label = self.classes[0] if self.classes else "Slots"
        return f"{label}()"


def _identity(x):
    return x


def _return_second(x, y):
    return y


def _is_fun(fn: object) -> bool:
    return callable(fn) and not inspect.isclass(fn)


def _params(fn: object) -> list[inspect.Parameter]:
    try:
        return list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return []


def _has_required(params: Sequence[inspect.Parameter]) -> bool:
    for param in params:
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if param.default is inspect.Parameter.empty:
            return True
    return False


def _one_arg_fun(fn: object) -> bool:
    if not _is_fun(fn):
        return False
    params = _params(fn)
    if len(params) < 1:
        return False
    if params[0].kind == inspect.Parameter.VAR_POSITIONAL:
        return False
    return not _has_required(params[1:])


def _dotted(key: str) -> str:
    if "." in key:
        return key
    return key.replace("_", ".")


def _normalize(kwargs: Mapping[str, object], allowed: Sequence[str]) -> dict[str, object]:
    allowed_set = set(allowed)
    out: dict[str, object] = {}
    for key, value in kwargs.items():
        name = _dotted(key)
        if name not in allowed_set:
            raise TypeError(f"invalid names for slots: '{key}'")
        if name in out:
            raise TypeError(f"Argument `{name}` specified twice")
        out[name] = value
    return out


def _has(kwargs: Mapping[str, object], name: str) -> bool:
    return name in kwargs or name.replace(".", "_") in kwargs


def _is_tf(value: object) -> bool:
    return value is True or value is False


def _is_int_1L(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        if not math.isfinite(value):
            return False
        return value == math.trunc(value)
    return True


def _is_chr_1L(value: object) -> bool:
    return isinstance(value, str)


def nchar2(x, *args, **kwargs):
    """``nchar`` or ``crayon.col_nchar``, picked by ``sgr.supported``."""

    if "sgr.supported" in kwargs:
        flag = kwargs.pop("sgr.supported")
    elif "sgr_supported" in kwargs:
        flag = kwargs.pop("sgr_supported")
    else:
        raise TypeError('argument "sgr.supported" is missing, with no default')
    if flag is True:
        return col_nchar(x, *args, **kwargs)
    if isinstance(x, str):
        return len(x)
    return [len(part) for part in x]


def _paste0(x, collapse: str = "") -> str:
    if isinstance(x, str):
        return x
    return collapse.join(x)


def _summary_container(x):
    return f"\n{_paste0(x, '')}\n"


def _summary_detail(x):
    parts = [x] if isinstance(x, str) else list(x)
    return "\n" + "".join(f"  {part}" for part in parts) + "\n"


def _summary_map(x):
    parts = [x] if isinstance(x, str) else list(x)
    return "\n" + "\n".join(f"  {part}" for part in parts)


def _html_summary_container(x):
    return div_f("diffobj-summary")(_paste0(x, ""))


def StyleFuns(**kwargs):
    """Formatting functions. Every slot starts as the identity."""

    values = {name: _identity for name in STYLE_FUN_SLOTS}
    values.update(_normalize(kwargs, STYLE_FUN_SLOTS))
    for name, fn in values.items():
        if not _is_fun(fn):
            raise ValueError(f"Argument `{name}` should be a function.")
        if _has_required(_params(fn)[1:]):
            raise ValueError(
                f"Argument `{name}` may not have non-default formals "
                "argument after the first."
            )
    return Slots(("StyleFuns",), values)


def _ansi_defaults() -> dict[str, object]:
    silver_slots = (
        "gutter.guide",
        "gutter.guide.ctd",
        "gutter.fill",
        "gutter.fill.ctd",
        "gutter.context.sep",
        "gutter.context.sep.ctd",
        "meta",
        "line.guide",
        "context.sep",
        "trim",
    )
    values = {name: _identity for name in STYLE_FUN_SLOTS}
    values["word.insert"] = green
    values["word.delete"] = red
    values["gutter.insert"] = green
    values["gutter.insert.ctd"] = green
    values["gutter.delete"] = red
    values["gutter.delete.ctd"] = red
    values["header"] = cyan
    for name in silver_slots:
        values[name] = silver
    return values


def StyleFunsAnsi(**kwargs):
    """``StyleFuns`` with the 8-color ANSI palette."""

    values = _ansi_defaults()
    values.update(_normalize(kwargs, STYLE_FUN_SLOTS))
    for name, fn in values.items():
        if not _is_fun(fn):
            raise ValueError(f"Argument `{name}` should be a function.")
        if _has_required(_params(fn)[1:]):
            raise ValueError(
                f"Argument `{name}` may not have non-default formals "
                "argument after the first."
            )
    return Slots(class_vector("StyleFunsAnsi"), values)


def StyleText(**kwargs):
    """Gutter tokens and separators."""

    values = {
        "gutter.insert": ">",
        "gutter.insert.ctd": ":",
        "gutter.delete": "<",
        "gutter.delete.ctd": ":",
        "gutter.match": " ",
        "gutter.match.ctd": " ",
        "gutter.guide": "~",
        "gutter.guide.ctd": "~",
        "gutter.fill": "~",
        "gutter.fill.ctd": "~",
        "gutter.context.sep": "~",
        "gutter.context.sep.ctd": "~",
        "gutter.pad": " ",
        "context.sep": "----------",
        "pad.col": "  ",
        "line.break": "\n",
    }
    values.update(_normalize(kwargs, STYLE_TEXT_SLOTS))
    for name, text in values.items():
        if not _is_chr_1L(text):
            raise ValueError(f"Argument `{name}` must be character(1L) and not NA.")
    return Slots(("StyleText",), values)


def StyleSummary(**kwargs):
    """Summary formatting functions."""

    values = {
        "container": _summary_container,
        "body": _identity,
        "detail": _summary_detail,
        "map": _summary_map,
    }
    values.update(_normalize(kwargs, STYLE_SUMMARY_SLOTS))
    for name, fn in values.items():
        if not _one_arg_fun(fn):
            raise ValueError(
                f"Slot {name} must contain a function that accepts at least one "
                "argument and requires no more than one argument."
            )
    return Slots(("StyleSummary",), values)


def StyleSummaryHtml(**kwargs):
    """HTML summary formatting functions."""

    values = {
        "container": _html_summary_container,
        "body": div_f("body"),
        "detail": div_f("detail"),
        "map": div_f("map"),
    }
    values.update(_normalize(kwargs, STYLE_SUMMARY_SLOTS))
    for name, fn in values.items():
        if not _one_arg_fun(fn):
            raise ValueError(
                f"Slot {name} must contain a function that accepts at least one "
                "argument and requires no more than one argument."
            )
    return Slots(class_vector("StyleSummaryHtml"), values)


def _file_show(x):
    return None


class _Pager(Slots):
    def __init__(self, kind: str, values: Mapping[str, object]):
        super().__init__(class_vector(kind), values)
        object.__setattr__(self, "kind", kind)


def _pager_base(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "pager": _file_show,
        "file.ext": "",
        "threshold": 0,
        "ansi": False,
        "file.path": None,
        "make.blocking": False,
    }
    values.update(overrides)
    return values


class PagerOff(_Pager):
    def __init__(self, **kwargs):
        values = _pager_base()
        values.update(_normalize(kwargs, values))
        super().__init__("PagerOff", values)


class PagerSystem(_Pager):
    def __init__(self, **kwargs):
        values = _pager_base()
        values["threshold"] = -1
        values["file.ext"] = ""
        values.update(_normalize(kwargs, list(values)))
        super().__init__("PagerSystem", values)


class PagerSystemLess(_Pager):
    def __init__(self, **kwargs):
        values = _pager_base()
        values["threshold"] = -1
        values["ansi"] = True
        values["file.ext"] = ""
        values["flags"] = "R"
        values.update(_normalize(kwargs, list(values)))
        super().__init__("PagerSystemLess", values)


class PagerBrowser(_Pager):
    def __init__(self, **kwargs):
        values = _pager_base()
        values["file.ext"] = "html"
        values["make.blocking"] = LOGICAL_NA
        values.update(_normalize(kwargs, list(values)))
        super().__init__("PagerBrowser", values)


def _system_pager():
    if pager_is_less():
        return PagerSystemLess()
    return PagerSystem()


def _check_file(name: str, path: object) -> None:
    if not _is_chr_1L(path):
        raise ValueError(f"Argument `{name}` must be character(1L) and not NA")
    if not os.path.isfile(path):
        raise ValueError(f'Argument `{name}` ("{path}") is not a file')


def _check_html_output(value: object) -> None:
    if not (_is_chr_1L(value) and value in _HTML_OUTPUTS):
        listed = 'c("auto", "page", "diff.only", "diff.w.style")'
        raise ValueError(f"Argument `html.output` must be in `{listed}`.")


def _validate_finalizer(fn: object) -> None:
    if not _is_fun(fn):
        raise ValueError("Slot `finalizer` must be a function with at least two parameters.")
    params = _params(fn)
    if len(params) < 2:
        raise ValueError("Slot `finalizer` must be a function with at least two parameters.")
    if _has_required(params[2:]):
        raise ValueError(
            "Slot `finalizer` must be a function with no non-default parameters "
            "other than the first two."
        )


def _validate_style(values: Mapping[str, object], html: bool) -> None:
    if not inherits(values["funs"], "StyleFuns"):
        raise TypeError("Slot `funs` must be a StyleFuns object")
    if not inherits(values["text"], "StyleText"):
        raise TypeError("Slot `text` must be a StyleText object")
    if not inherits(values["summary"], "StyleSummary"):
        raise TypeError("Slot `summary` must be a StyleSummary object")
    if not _is_tf(values["wrap"]):
        raise ValueError("Slot `wrap` must be TRUE or FALSE")
    if not _is_tf(values["pad"]):
        raise ValueError("Slot `pad` must be TRUE or FALSE")
    if not isinstance(values["na.sub"], str):
        raise ValueError("Slot `na.sub` must be character(1L)")
    if not isinstance(values["blank.sub"], str):
        raise ValueError("Slot `na.sub` must be character(1L)")
    if not _is_int_1L(values["disp.width"]) or values["disp.width"] < 0:
        raise ValueError("Slot `disp.width` must be integer(1L), positive, and not NA")
    _validate_finalizer(values["finalizer"])
    if html:
        if not _is_chr_1L(values["css"]):
            raise ValueError("slot `css` must be character(1L)")
        if not _is_chr_1L(values["js"]):
            raise ValueError("slot `js` must be character(1L)")
        if not _is_chr_1L(values["html.output"]):
            raise ValueError("slot `html.output` must be character(1L)")
        if not _is_tf(values["escape.html.entities"]):
            raise ValueError("slot `escape.html.entities` must be TRUE or FALSE.")
        if not _is_tf(values["scale"]):
            raise ValueError("slot `scale` must be TRUE or FALSE.")
        if values["wrap"] is not False:
            raise ValueError("slot `wrap` must be FALSE for `styleHtml` objects.")


def _base_defaults() -> dict[str, object]:
    return {
        "funs": StyleFuns(),
        "text": StyleText(),
        "summary": StyleSummary(),
        "nchar.fun": nchar2,
        "wrap": True,
        "pad": True,
        "finalizer": _return_second,
        "pager": PagerOff(),
        "na.sub": "",
        "blank.sub": "",
        "disp.width": 0,
    }


def _html_funs():
    return StyleFuns(
        **{
            "container": cont_f(),
            "row": div_f("diffobj-row"),
            "banner.insert": div_f("insert"),
            "banner.delete": div_f("delete"),
            "banner": div_f("diffobj-line banner"),
            "line.insert": div_f("insert"),
            "line.delete": div_f("delete"),
            "line.match": div_f("diffobj-match"),
            "line.guide": div_f("diffobj-guide"),
            "line.fill": div_f("diffobj-fill"),
            "line": div_f("diffobj-line"),
            "text.insert": div_f("insert"),
            "text.delete": div_f("delete"),
            "text.match": div_f("diffobj-match"),
            "text.guide": div_f("diffobj-guide"),
            "text.fill": div_f("diffobj-fill"),
            "text": div_f("diffobj-text"),
            "gutter.insert": div_f("insert"),
            "gutter.delete": div_f("delete"),
            "gutter.match": div_f("diffobj-match"),
            "gutter.guide": div_f("diffobj-guide"),
            "gutter.fill": div_f("diffobj-fill"),
            "gutter.pad": div_f("pad"),
            "gutter.context.sep": div_f(("context_sep", "ctd")),
            "gutter.insert.ctd": div_f(("insert", "ctd")),
            "gutter.delete.ctd": div_f(("delete", "ctd")),
            "gutter.match.ctd": div_f(("diffobj-match", "ctd")),
            "gutter.guide.ctd": div_f(("diffobj-guide", "ctd")),
            "gutter.fill.ctd": div_f(("diffobj-fill", "ctd")),
            "gutter.context.sep.ctd": div_f(("context_sep", "ctd")),
            "gutter": div_f("diffobj-gutter"),
            "context.sep": div_f("context_sep"),
            "word.insert": span_f(("diffobj-word", "insert")),
            "word.delete": span_f(("diffobj-word", "delete")),
            "trim": span_f("diffobj-trim"),
            "header": div_f("diffobj-header"),
        }
    )


def _html_text():
    return StyleText(
        **{
            "gutter.insert": "&gt;",
            "gutter.delete": "&lt;",
            "gutter.match": "&nbsp;",
            "line.break": "<br />",
            "pad.col": "",
        }
    )


def _html_defaults() -> dict[str, object]:
    values = _base_defaults()
    values.update(
        {
            "funs": _html_funs(),
            "text": _html_text(),
            "summary": StyleSummaryHtml(),
            "pager": PagerBrowser(),
            "wrap": False,
            "pad": False,
            "nchar.fun": nchar_html,
            "na.sub": "&nbsp;",
            "blank.sub": "&nbsp;",
            "disp.width": 80,
            "finalizer": finalizeHtml,
            "css": "",
            "html.output": "auto",
            "escape.html.entities": True,
            "js": "",
            "scale": True,
        }
    )
    return values


def _apply_html_initialize(mapped: dict[str, object]) -> dict[str, object]:
    # The R initializer reads escape.html.entities and then does not pass it
    # on, so the prototype TRUE stays in place.
    mapped.pop("escape.html.entities", None)
    if "css" in mapped:
        css = mapped["css"]
    else:
        css = gdo("html.css")
        if css is None:
            css = diffobj_css()
    _check_file("css", css)
    if "js" in mapped:
        js = mapped["js"]
    else:
        js = gdo("html.js")
        if js is None:
            js = diffobj_js()
    _check_file("js", js)
    if "html.output" in mapped:
        html_output = mapped["html.output"]
    else:
        html_output = gdo("html.output")
        if html_output is None:
            html_output = "auto"
    _check_html_output(html_output)
    if "scale" in mapped:
        scale = mapped["scale"]
    else:
        scale = gdo("html.scale")
        if scale is None:
            scale = True
    if not _is_tf(scale):
        raise ValueError("Argument `scale` must be TRUE or FALSE")
    mapped["css"] = css
    mapped["js"] = js
    mapped["html.output"] = html_output
    mapped["scale"] = scale
    return mapped


def _new_style(class_name: str, *, html: bool = False, **kwargs):
    allowed = STYLE_SLOTS + HTML_SLOTS if html else STYLE_SLOTS
    mapped = _normalize(kwargs, allowed)
    if html:
        mapped = _apply_html_initialize(mapped)
    defaults = _html_defaults() if html else _base_defaults()
    for key, value in defaults.items():
        mapped.setdefault(key, value)
    if _is_int_1L(mapped["disp.width"]):
        mapped["disp.width"] = int(mapped["disp.width"])
    _validate_style(mapped, html=html)
    return Slots(class_vector(class_name), mapped)


def Style(**kwargs):
    """Virtual base class. R refuses to construct it."""

    del kwargs
    raise ValueError('trying to generate an object from a virtual class ("Style")')


def StyleRaw(**kwargs):
    """Plain text. Uses less when that is the system pager."""

    kwargs = dict(kwargs)
    if not _has(kwargs, "pager"):
        kwargs["pager"] = _system_pager()
    return _new_style("StyleRaw", **kwargs)


def _new_ansi(class_name: str, funs, **kwargs):
    kwargs = dict(kwargs)
    if not _has(kwargs, "pager"):
        kwargs["pager"] = _system_pager()
    if not _has(kwargs, "nchar.fun"):
        kwargs["nchar.fun"] = col_nchar
    if not _has(kwargs, "funs"):
        kwargs["funs"] = funs
    return _new_style(class_name, **kwargs)


def StyleAnsi(**kwargs):
    """8-color ANSI style. Insertions are green and deletions are red."""

    return _new_ansi("StyleAnsi", StyleFunsAnsi(), **kwargs)


def StyleAnsi8NeutralRgb(**kwargs):
    """8-color neutral red/green style."""

    return _new_ansi("StyleAnsi8NeutralRgb", StyleFunsAnsi(), **kwargs)


def StyleAnsi8NeutralYb(**kwargs):
    """8-color neutral yellow/blue style."""

    funs = StyleFunsAnsi(
        **{
            "word.insert": blue,
            "word.delete": yellow,
            "gutter.insert": blue,
            "gutter.insert.ctd": blue,
            "gutter.delete": yellow,
            "gutter.delete.ctd": yellow,
        }
    )
    return _new_ansi("StyleAnsi8NeutralYb", funs, **kwargs)


def _color(r: int, g: int, b: int, maximum: int, *, bg: bool = False, grey: bool = False):
    return make_style(rgb(r, g, b, maxColorValue=maximum), bg=bg, grey=grey, colors=256)


def _with_ctd(values: dict[str, object], name: str, style) -> None:
    values[name] = style
    values[name + ".ctd"] = style


def _grey13():
    return _color(13, 13, 13, 23, grey=True)


def _dark_chrome(values: dict[str, object]) -> None:
    guide = _grey13()
    _with_ctd(values, "gutter.guide", guide)
    values["line.guide"] = guide
    _with_ctd(values, "gutter.fill", guide)
    values["text.fill"] = _color(2, 2, 2, 23, bg=True, grey=True)
    _with_ctd(values, "gutter.context.sep", guide)
    values["context.sep"] = guide
    values["meta"] = guide
    values["trim"] = guide


def _light_rgb_funs():
    values: dict[str, object] = {}
    values["text.insert"] = _color(4, 5, 4, 5, bg=True)
    values["text.delete"] = _color(5, 4, 4, 5, bg=True)
    values["text.fill"] = _color(20, 20, 20, 23, bg=True, grey=True)
    values["word.insert"] = _color(2, 4, 2, 5, bg=True)
    values["word.delete"] = _color(4, 2, 2, 5, bg=True)
    _with_ctd(values, "gutter.insert", _color(0, 3, 0, 5))
    _with_ctd(values, "gutter.delete", _color(3, 0, 0, 5))
    values["header"] = _color(0, 3, 3, 5)
    return StyleFunsAnsi(**values)


def _light_yb_funs():
    values: dict[str, object] = {}
    values["text.insert"] = _color(3, 3, 5, 5, bg=True)
    values["text.delete"] = _color(4, 4, 2, 5, bg=True)
    values["text.fill"] = _color(20, 20, 20, 23, bg=True, grey=True)
    values["word.insert"] = _color(2, 2, 4, 5, bg=True)
    values["word.delete"] = _color(3, 3, 1, 5, bg=True)
    _with_ctd(values, "gutter.insert", _color(0, 0, 3, 5))
    _with_ctd(values, "gutter.delete", _color(2, 1, 0, 5))
    values["header"] = _color(0, 3, 3, 5)
    return StyleFunsAnsi(**values)


def _dark_rgb_funs():
    values: dict[str, object] = {}
    values["text.insert"] = _color(0, 1, 0, 5, bg=True)
    values["text.delete"] = _color(1, 0, 0, 5, bg=True)
    values["word.insert"] = _color(0, 3, 0, 5, bg=True)
    values["word.delete"] = _color(3, 0, 0, 5, bg=True)
    _with_ctd(values, "gutter.insert", _color(0, 2, 0, 5))
    _with_ctd(values, "gutter.delete", _color(2, 0, 0, 5))
    _dark_chrome(values)
    return StyleFunsAnsi(**values)


def _dark_yb_funs():
    values: dict[str, object] = {}
    values["text.insert"] = _color(0, 0, 2, 5, bg=True)
    values["text.delete"] = _color(1, 1, 0, 5, bg=True)
    values["word.insert"] = _color(0, 0, 5, 5, bg=True)
    values["word.delete"] = _color(3, 2, 0, 5, bg=True)
    _with_ctd(values, "gutter.insert", _color(0, 0, 3, 5))
    _with_ctd(values, "gutter.delete", _color(1, 1, 0, 5))
    values["header"] = _color(0, 3, 3, 5)
    _dark_chrome(values)
    return StyleFunsAnsi(**values)


def StyleAnsi256LightRgb(**kwargs):
    """256-color light red/green style."""

    return _new_ansi("StyleAnsi256LightRgb", _light_rgb_funs(), **kwargs)


def StyleAnsi256LightYb(**kwargs):
    """256-color light yellow/blue style."""

    return _new_ansi("StyleAnsi256LightYb", _light_yb_funs(), **kwargs)


def StyleAnsi256DarkRgb(**kwargs):
    """256-color dark red/green style."""

    return _new_ansi("StyleAnsi256DarkRgb", _dark_rgb_funs(), **kwargs)


def StyleAnsi256DarkYb(**kwargs):
    """256-color dark yellow/blue style."""

    return _new_ansi("StyleAnsi256DarkYb", _dark_yb_funs(), **kwargs)


def _new_html(class_name: str, **kwargs):
    return _new_style(class_name, html=True, **kwargs)


def StyleHtml(**kwargs):
    """HTML style. ``html.output`` starts as ``auto``."""

    return _new_html("StyleHtml", **kwargs)


def StyleHtmlLightRgb(**kwargs):
    """Light red/green HTML style."""

    passed_funs = _has(kwargs, "funs")
    obj = _new_html("StyleHtmlLightRgb", **kwargs)
    if not passed_funs:
        obj.funs.container = cont_f(("light", "rgb"))
    return obj


def StyleHtmlLightYb(**kwargs):
    """Light yellow/blue HTML style."""

    passed_funs = _has(kwargs, "funs")
    obj = _new_html("StyleHtmlLightYb", **kwargs)
    if not passed_funs:
        obj.funs.container = cont_f(("light", "yb"))
    return obj


class _Dimnames(dict):
    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)


class _PaletteData:
    def __init__(self):
        self.dim = (4, 3, 2)
        self.shape = self.dim
        names = _Dimnames(
            (
                ("format", ("raw", "ansi8", "ansi256", "html")),
                ("brightness", ("neutral", "light", "dark")),
                ("color.mode", ("rgb", "yb")),
            )
        )
        for key, value in names.items():
            object.__setattr__(names, key, value)
        self.dimnames = names
        self._cells: list[object] = [None] * 24
        self._fill()

    def _pos(self, fmt: str, brightness: str, color_mode: str) -> int:
        i = self.dimnames["format"].index(fmt)
        j = self.dimnames["brightness"].index(brightness)
        k = self.dimnames["color.mode"].index(color_mode)
        return i + 4 * j + 12 * k

    def __getitem__(self, key):
        if not isinstance(key, tuple) or len(key) != 3:
            raise KeyError(key)
        return self._cells[self._pos(*key)]

    def __setitem__(self, key, value) -> None:
        if not isinstance(key, tuple) or len(key) != 3:
            raise KeyError(key)
        self._cells[self._pos(*key)] = value

    def _fill_all(self, fmt: str, color_mode: str, factory) -> None:
        for brightness in self.dimnames["brightness"]:
            self[fmt, brightness, color_mode] = factory

    def _fill(self) -> None:
        for brightness in self.dimnames["brightness"]:
            for color_mode in self.dimnames["color.mode"]:
                self["raw", brightness, color_mode] = StyleRaw
        self._fill_all("ansi8", "rgb", StyleAnsi8NeutralRgb)
        self._fill_all("ansi8", "yb", StyleAnsi8NeutralYb)
        self["ansi256", "neutral", "rgb"] = StyleAnsi8NeutralRgb
        self["ansi256", "neutral", "yb"] = StyleAnsi8NeutralYb
        self["ansi256", "light", "rgb"] = StyleAnsi256LightRgb
        self["ansi256", "light", "yb"] = StyleAnsi256LightYb
        self["ansi256", "dark", "rgb"] = StyleAnsi256DarkRgb
        self["ansi256", "dark", "yb"] = StyleAnsi256DarkYb
        self._fill_all("html", "rgb", StyleHtmlLightRgb)
        self._fill_all("html", "yb", StyleHtmlLightYb)


def PaletteOfStyles(**kwargs):
    """The format, brightness, and color-mode array of style constructors."""

    if kwargs:
        raise TypeError("PaletteOfStyles does not take slots other than data")
    return Slots(("PaletteOfStyles",), {"data": _PaletteData()})


def _coerce_min_chars(value: object) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    return value


def AlignThreshold(
    threshold: object = _MISSING,
    min_chars: object = _MISSING,
    count_alnum_only: object = _MISSING,
    **kwargs,
):
    """How similar two lines must be before the diff aligns them."""

    if "min.chars" in kwargs:
        if min_chars is not _MISSING:
            raise TypeError("Argument `min.chars` specified twice")
        min_chars = kwargs.pop("min.chars")
    if "count.alnum.only" in kwargs:
        if count_alnum_only is not _MISSING:
            raise TypeError("Argument `count.alnum.only` specified twice")
        count_alnum_only = kwargs.pop("count.alnum.only")
    if kwargs:
        unknown = ", ".join(kwargs)
        raise TypeError(f"invalid names for slots: '{unknown}'")
    if threshold is _MISSING:
        threshold = gdo("align.threshold")
    if min_chars is _MISSING:
        min_chars = gdo("align.min.chars")
    if count_alnum_only is _MISSING:
        count_alnum_only = gdo("align.count.alnum.only")
    min_chars = _coerce_min_chars(min_chars)
    bad_threshold = (
        isinstance(threshold, (list, tuple))
        or isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or (isinstance(threshold, float) and not math.isfinite(threshold))
        or not (0 <= threshold <= 1)
    )
    if bad_threshold:
        raise ValueError("Slot `threhold` must be numeric(1L) between 0 and 1")
    if isinstance(min_chars, bool) or not isinstance(min_chars, int) or min_chars < 0:
        raise ValueError("Slot `min.chars` must be integer(1L) and positive")
    if not _is_tf(count_alnum_only):
        raise ValueError("Slot `count.alnum.only` must be TRUE or FALSE")
    return Slots(
        ("AlignThreshold",),
        {
            "threshold": threshold,
            "min.chars": min_chars,
            "count.alnum.only": count_alnum_only,
        },
    )


def _character_vector(value: object, name: str) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        out: list[str] = []
        for item in value:
            if item is None:
                out.append("NA")
            elif isinstance(item, str):
                out.append(item)
            else:
                raise TypeError(f"Argument `{name}` must be character")
        return out
    raise TypeError(f"Argument `{name}` must be character")


def _style_of(x: object):
    etc = x.get("etc") if isinstance(x, Mapping) else getattr(x, "etc", None)
    if etc is None:
        raise AttributeError("x must expose etc.style")
    if isinstance(etc, Mapping):
        return etc["style"]
    return getattr(etc, "style")


def _read_text(path: object) -> str | None:
    label = path if isinstance(path, str) else ""
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError:
        warnings.warn(
            f'Unable to read provided css file "{label}" '
            "(error: cannot open the connection).",
            UserWarning,
            stacklevel=3,
        )
        return None
    return "\n".join(text.splitlines())


def _enc2utf8(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    for item in values:
        out.append(item.encode("utf-8", "surrogateescape").decode("utf-8", "replace"))
    return out


def finalizeHtml(x, x_chr=_MISSING, js=_MISSING, **kwargs):
    """Wrap HTML diff text according to ``style@html.output``."""

    if "x.chr" in kwargs:
        if x_chr is not _MISSING:
            raise TypeError("finalizeHtml() got multiple values for argument 'x.chr'")
        x_chr = kwargs.pop("x.chr")
    if x_chr is _MISSING:
        raise TypeError('argument "x.chr" is missing, with no default')
    if js is _MISSING:
        raise TypeError('argument "js" is missing, with no default')
    try:
        text = _character_vector(x_chr, "x.chr")
    except TypeError:
        raise TypeError("Argument `x.chr` must be character") from None
    if not _is_chr_1L(js):
        raise TypeError("Argument `js` must be character(1L) and not NA.")
    style = _style_of(x)
    html_output = style.html_output
    pager = style.pager
    if html_output == "auto":
        html_output = "page" if inherits(pager, "PagerBrowser") else "diff.only"
    css = ""
    if html_output in ("diff.w.style", "page"):
        css_txt = _read_text(style.css)
        if css_txt is None:
            css = ""
        else:
            css = f"<style type='text/css'>\n{css_txt}\n</style>"
    if html_output == "diff.w.style":
        template = "%s%s"
    elif html_output == "page":
        text = _enc2utf8(text)
        template = _PAGE % (_CHARSET, js)
    elif html_output == "diff.only":
        css = ""
        template = "%s%s"
    else:
        raise RuntimeError("Internal Error: unexpected html.output; contact maintainer.")
    return template % (css, "".join(text))


__all__ = [
    "AlignThreshold",
    "PaletteOfStyles",
    "Style",
    "StyleAnsi",
    "StyleAnsi256DarkRgb",
    "StyleAnsi256DarkYb",
    "StyleAnsi256LightRgb",
    "StyleAnsi256LightYb",
    "StyleAnsi8NeutralRgb",
    "StyleAnsi8NeutralYb",
    "StyleFuns",
    "StyleHtml",
    "StyleHtmlLightRgb",
    "StyleHtmlLightYb",
    "StyleRaw",
    "StyleSummary",
    "StyleSummaryHtml",
    "StyleText",
    "finalizeHtml",
    "inherits",
]
