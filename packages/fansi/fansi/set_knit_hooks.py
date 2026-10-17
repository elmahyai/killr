"""knitr output hooks that turn CSI SGR into HTML, from set_knit_hooks in R/misc.R."""

from __future__ import annotations

import inspect
import warnings

from fansi._args import FansiError, option, prepare
from fansi._const import (
    BRD_ENCIRC,
    BRD_FRAMED,
    BRD_OVERLN,
    CLR_256,
    CLR_8,
    CLR_BRIGHT,
    CLR_TRU,
    CTL_SGR,
    FONT_ALL,
    FONT_START,
    IDG_OVERL,
    IDG_OVERL2,
    IDG_STRESS,
    IDG_UNDERL,
    IDG_UNDERL2,
    STL_BLINK1,
    STL_BLINK2,
    STL_BLUR,
    STL_BOLD,
    STL_CONCEAL,
    STL_CROSSOUT,
    STL_FRAKTUR,
    STL_INVERT,
    STL_ITALIC,
    STL_PROPSPC,
    STL_UNDER,
    STL_UNDER2,
    WARN_MASK,
)
from fansi._read import read_next
from fansi._state import state_init_full
from fansi.has_ctl import has_ctl
from fansi.html_esc import html_esc
from fansi.simple import dflt_css, dflt_term_cap, html_code_block
from fansi.to_html import to_html

# CLR_MASK is 240 in the C headers. Importing the color modes above is enough.
_CLR_MASK = 240
_WHICH = ("output", "warning", "error", "message")
_BASE_ERR = "are you sure you passed `knitr::knit_hooks` as the `hooks` argument?"


def _default_proc(x, class_):
    return html_code_block(to_html(html_esc(x)), class_=class_)


def _character(value, name):
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return list(value)
    raise FansiError(f"Argument `{name}` must be character.")


def _sgr_active(sgr):
    return bool(sgr.style or sgr.color.x or sgr.bgcol.x)


def _color_token(color, mode):
    clrval = color.x & ~_CLR_MASK
    if (color.x & _CLR_MASK) == CLR_BRIGHT:
        if mode == 3:
            return f"9{clrval}"
        return f"10{clrval}"
    token = f"{mode}{clrval}"
    if color.x & CLR_TRU:
        extra = color.extra
        token += f";2;{extra[0]};{extra[1]};{extra[2]}"
    elif color.x & CLR_256:
        token += f";5;{color.extra[0]}"
    elif not (color.x & CLR_8):
        raise FansiError("Internal Error: unexpected color mode.")
    return token


def _sgr_open(sgr):
    """Canonical opening sequence, normalize = FALSE and enclose = TRUE."""
    if not _sgr_active(sgr):
        return b""
    style = sgr.style
    tokens = []
    for bit, label in (
        (STL_BOLD, "1"),
        (STL_BLUR, "2"),
        (STL_ITALIC, "3"),
        (STL_UNDER, "4"),
        (STL_BLINK1, "5"),
        (STL_BLINK2, "6"),
        (STL_INVERT, "7"),
        (STL_CONCEAL, "8"),
        (STL_CROSSOUT, "9"),
        (STL_FRAKTUR, "20"),
        (STL_UNDER2, "21"),
        (STL_PROPSPC, "26"),
    ):
        if style & bit:
            tokens.append(label)
    if sgr.color.x:
        tokens.append(_color_token(sgr.color, 3))
    if sgr.bgcol.x:
        tokens.append(_color_token(sgr.bgcol, 4))
    for bit, label in (
        (BRD_FRAMED, "51"),
        (BRD_ENCIRC, "52"),
        (BRD_OVERLN, "53"),
        (IDG_UNDERL, "60"),
        (IDG_UNDERL2, "61"),
        (IDG_OVERL, "62"),
        (IDG_OVERL2, "63"),
        (IDG_STRESS, "64"),
    ):
        if style & bit:
            tokens.append(label)
    font = (style >> FONT_START) & FONT_ALL
    if font:
        tokens.append(f"1{font % 10}")
    return ("\033[" + ";".join(tokens) + "m").encode("ascii")


def _split_one(text, warn_int, term_int):
    """strsplit_sgr on a newline: SGR-aware pieces with an explicit closer."""
    data = text.encode("utf-8", "surrogateescape")
    state = state_init_full([text], warn_int, term_int, True, False, 0, [4], 0)
    chars = []
    escapes = []
    states = []
    pending = bytearray()
    pos = 0
    limit = len(data)
    while pos < limit and data[pos]:
        if data[pos] == 0x1B:
            state.pos_x = pos
            read_next(state, 0, "x")
            if state.status & CTL_SGR:
                pending += data[pos:state.pos_x]
                pos = state.pos_x
                continue
            chars.append(data[pos:state.pos_x])
            escapes.append(bytes(pending))
            states.append(state.fmt.sgr.copy())
            pending.clear()
            pos = state.pos_x
            continue
        start = pos
        state.pos_x = pos
        read_next(state, 0, "x")
        chars.append(data[start:state.pos_x])
        escapes.append(bytes(pending))
        states.append(state.fmt.sgr.copy())
        pending.clear()
        pos = state.pos_x
    count = len(chars)
    if count == 0:
        return []
    newlines = [index + 1 for index, char in enumerate(chars) if char == b"\n"]
    if not newlines:
        return [text]
    starts = [1] + [match + 1 for match in newlines]
    ends = [match - 1 for match in newlines] + [count]
    pieces = []
    for start, end in zip(starts, ends):
        if start < 1:
            start = 1
        if start > count:
            continue
        if start > end:
            pieces.append("")
            continue
        out = bytearray()
        opening = states[start - 1]
        if _sgr_active(opening):
            out += _sgr_open(opening)
        for index in range(start - 1, end):
            if index != start - 1 and escapes[index]:
                out += escapes[index]
            out += chars[index]
        if _sgr_active(states[end - 1]):
            out += b"\033[0m"
        pieces.append(out.decode("utf-8", "surrogateescape"))
    return pieces


def _split_newlines(x):
    warn = option("fansi.warn", True)
    stored = option("fansi.term.cap", None)
    term_cap = dflt_term_cap() if stored is None else stored
    checked = prepare(
        x=[""], warn=warn, term_cap=term_cap, warn_mask=WARN_MASK, coerce_x=False
    )
    texts = x if isinstance(x, (list, tuple)) else [x]
    pieces = []
    for text in texts:
        if text is None:
            pieces.append(None)
        elif isinstance(text, str):
            pieces.extend(
                _split_one(text, checked["warn_int"], checked["term_cap_int"])
            )
        else:
            raise FansiError("Argument `x` must be character.")
    return pieces


def _any_special(flags):
    saw_missing = False
    for flag in flags:
        if flag is True:
            return True
        if flag is None:
            saw_missing = True
    if saw_missing:
        raise FansiError("missing value where TRUE/FALSE needed")
    return False


def _formals_ok(proc_fun):
    try:
        parameters = inspect.signature(proc_fun).parameters
    except (TypeError, ValueError):
        return False
    names = set(parameters)
    return "x" in names and ("class_" in names or "class" in names)


def _call_proc(proc_fun, x, class_):
    parameters = inspect.signature(proc_fun).parameters
    if "class_" in parameters:
        return proc_fun(x=x, class_=class_)
    return proc_fun(x=x, **{"class": class_})


def set_knit_hooks(
    hooks,
    which="output",
    proc_fun=None,
    class_=None,
    style=None,
    split_nl=False,
    _test=False,
):
    """Replace knitr output hooks and write a STYLE block. Returns the old hooks."""
    getter = getattr(hooks, "get", None)
    setter = getattr(hooks, "set", None)
    if not callable(getter) or not callable(setter):
        raise FansiError("Argument `hooks` does not appear to be `knitr::knit_hooks`.")
    try:
        names = _character(which, "which")
    except FansiError:
        shown = "c(" + ", ".join(f'"{name}"' for name in _WHICH) + ")"
        raise FansiError(
            "Argument `which` must be character containing values in " + shown
        ) from None
    if any(name not in _WHICH for name in names):
        shown = "c(" + ", ".join(f'"{name}"' for name in _WHICH) + ")"
        raise FansiError(
            "Argument `which` must be character containing values in " + shown
        )
    seen = set()
    for name in names:
        if name in seen:
            raise FansiError(
                f"Argument `which` may not contain duplicate values ({name})."
            )
        seen.add(name)
    if proc_fun is None:
        proc_fun = _default_proc
    if not _formals_ok(proc_fun):
        raise FansiError(
            "Argument `proc.fun` must be a function with formals named "
            "`x` and `class`."
        )
    if class_ is None:
        classes = [f"fansi fansi-{name}" for name in names]
    else:
        try:
            classes = _character(class_, "class")
        except FansiError:
            raise FansiError(
                "Argument `class` should be a character vector the same length "
                "as `which`."
            ) from None
        if len(classes) != len(names):
            raise FansiError(
                "Argument `class` should be a character vector the same length "
                "as `which`."
            )
    if style is None:
        stored = option("fansi.css", None)
        style = dflt_css() if stored is None else stored
    try:
        style_lines = _character(style, "style")
    except FansiError:
        raise FansiError("Argument `style` must be character.") from None
    if not isinstance(split_nl, bool):
        raise FansiError("Argument `split.n` must be TRUE or FALSE")
    if proc_fun is _default_proc:
        bound = _default_proc
    else:
        bound = proc_fun

    def make_hook(old_hook, class_name, split):
        def hook(x, options):
            if _any_special(has_ctl(x, ["sgr", "url"])):
                material = _split_newlines(x) if split else x
                try:
                    return _call_proc(bound, material, class_name)
                except Exception as exc:
                    raise FansiError(
                        "Argument `proc.fun` for `set_knit_hooks` caused an error "
                        "when processing output; see prior error."
                    ) from exc
            return old_hook(x, options)

        return hook

    old_hooks = {name: None for name in names}
    new_hooks = {name: None for name in names}
    for index, name in enumerate(names):
        try:
            old_hook = getter(name)
        except Exception:
            warnings.warn(
                f"Failed retrieving '{name}' hook from the knit hooks; "
                f"{_BASE_ERR}  Quitting after setting {index}/{len(names)} hooks",
                UserWarning,
                stacklevel=2,
            )
            break
        if not callable(old_hook):
            warnings.warn(
                f"Retrieved '{name}' hook is not a function; "
                f"{_BASE_ERR}  Quitting after setting {index}/{len(names)} hooks",
                UserWarning,
                stacklevel=2,
            )
            break
        new_hooks[name] = make_hook(old_hook, classes[index], split_nl)
        old_hooks[name] = old_hook
    set_result = None
    try:
        set_result = setter(**new_hooks)
    except Exception:
        warnings.warn(
            "Failure while trying to set hooks; see prior error; " + _BASE_ERR,
            UserWarning,
            stacklevel=2,
        )
    for line in ("<STYLE type='text/css' scoped>", *style_lines, "</STYLE>"):
        print(line)
    if _test:
        return {"old.hooks": old_hooks, "new.hooks": new_hooks, "res": set_result}
    return old_hooks
