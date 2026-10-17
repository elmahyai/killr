"""Functions that do not parse control sequences."""

from __future__ import annotations

import math
import os
import tempfile
import time
import webbrowser

from fansi._args import FansiError
from fansi._width import UNICODE_VERSION


def dflt_term_cap():
    """Terminal capabilities assumed when `term.cap` is left unset."""
    colorterm = os.environ.get("COLORTERM", "")
    caps = []
    if colorterm in ("truecolor", "24bit"):
        caps.append("truecolor")
    caps.extend(("bright", "256"))
    return caps


def dflt_css():
    """Default CSS used when framing HTML."""
    return "PRE.fansi SPAN {padding-top: .25em; padding-bottom: .25em};"


def fansi_unicode_version():
    """Unicode database version used for display widths."""
    return UNICODE_VERSION


def _require_step(step):
    if isinstance(step, bool) or not isinstance(step, (int, float)):
        raise FansiError("Argument `step` must be a strictly positive scalar integer.")
    if isinstance(step, float) and step != step:
        raise FansiError("Argument `step` must be a strictly positive scalar integer.")
    if step < 1:
        raise FansiError("Argument `step` must be a strictly positive scalar integer.")
    return int(step)


def _as_lines(txt):
    if isinstance(txt, str):
        return [txt]
    if isinstance(txt, (list, tuple)):
        lines = []
        for item in txt:
            if item is None:
                lines.append(None)
            elif isinstance(item, str):
                lines.append(item)
            elif isinstance(item, bool):
                lines.append("TRUE" if item else "FALSE")
            elif isinstance(item, int):
                lines.append(str(item))
            elif isinstance(item, float):
                if item != item:
                    lines.append(None)
                elif item.is_integer():
                    lines.append(str(int(item)))
                else:
                    lines.append(str(item))
            else:
                lines.append(str(item))
        return lines
    if txt is None:
        return [None]
    return [str(txt)]


def fansi_lines(txt, step=1):
    """Color each element with a 256-color background."""
    lines = _as_lines(txt)
    step = _require_step(step)
    out = list(lines)
    for index, text in enumerate(lines, start=1):
        if text is None or text == "":
            continue
        bg = math.ceil((index * step) % 215 + 1) + 16
        fg = 30 if (((bg - 16) // 18) % 2) else 37
        out[index - 1] = f"\033[{fg};48;5;{bg}m{text}\033[39;49m"
    return out


def _format_char(values):
    width = max((len(value) for value in values), default=0)
    return [value.ljust(width) for value in values]


def _format_int(value, width):
    return str(value).rjust(width)


def term_cap_test():
    """Print bright, 256, and truecolor samples and return the samples."""
    labels = _format_char(["bright", "256", "truecolor"])
    opens = (
        "\033[91;104m",
        "\033[38;5;196;48;5;21m",
        "\033[38;2;255;0;0;48;2;0;0;255m",
    )
    samples = [open_ + label + "\033[0m" for open_, label in zip(opens, labels)]
    escaped = _format_char([sample.replace("\033", "\\033") for sample in samples])
    for sample, shown in zip(samples, escaped):
        print(sample + "  ->  " + shown)
    return samples


def sgr_256():
    """Show each 8-bit SGR code on its own background."""
    template = "\033[38;5;%d;48;5;%dm%s\033[m"

    def joined(fg, start, stop):
        return " ".join(
            template % (fg, bg, _format_int(bg, 3)) for bg in range(start, stop)
        )

    basic = joined(15, 0, 8)
    bright = joined(0, 8, 16)
    gray_dark = joined(15, 232, 244)
    gray_light = joined(0, 244, 256)
    fg = list(range(231, 15, -1))
    bg = list(reversed(fg))
    label_width = max(len(str(value)) for value in bg)
    cells = [
        template % (fore, back, _format_int(back, label_width))
        for fore, back in zip(fg, bg)
    ]

    def block(row_start, row_stop):
        lines = []
        for column in range(6):
            lines.append(
                "".join(cells[row + column * 36] for row in range(row_start, row_stop))
            )
        return lines

    return [
        "Standard",
        basic,
        "",
        "High-Intensity",
        bright,
        "",
        "216 Colors (Dark)",
        *block(0, 18),
        "",
        "216 Colors (Light)",
        *block(18, 36),
        "",
        "Grayscale",
        gray_dark,
        gray_light,
    ]


def fwl(*parts, end="<END>\033[0m"):
    """Print strings and finish with a reset sequence."""
    for part in (*parts, end):
        if isinstance(part, (list, tuple)):
            for line in part:
                print("" if line is None else line)
        else:
            print("" if part is None else part)
    return None


def _character_vector(value, name):
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return list(value)
    kind = "NULL" if value is None else type(value).__name__
    raise FansiError(f"Argument `{name}` must be character, is {kind}.")


def html_code_block(x, class_="fansi-output"):
    """Wrap lines in the PRE/CODE tags knitr puts around chunk output."""
    lines = _character_vector(x, "x")
    classes = _character_vector(class_, "class")
    class_attr = 'class="%s"' % " ".join(classes)
    body = "\n".join(lines)
    return f"<PRE {class_attr}><CODE>{body}</CODE></PRE>"


def in_html(x, css=None, pre=True, display=True, clean=None):
    """Write HTML to a temporary file and optionally open it."""
    if css is None:
        css = []
    lines = _character_vector(x, "x")
    styles = _character_vector(css, "css") if css != [] else []
    if not isinstance(pre, bool):
        raise FansiError("Argument `pre` must be TRUE or FALSE.")
    if not isinstance(display, bool):
        raise FansiError("Argument `display` must be TRUE or FALSE.")
    if clean is None:
        clean = display
    if not isinstance(clean, bool):
        raise FansiError("Argument `clean` must be TRUE or FALSE.")
    html = ["<!DOCTYPE html>", "<html>"]
    if any(style != "" for style in styles):
        html.extend(["<style>", *styles, "</style>"])
    html.append("<body>")
    if pre:
        html.append("<pre>")
    html.extend(lines)
    if pre:
        html.append("</pre>")
    html.extend(["</body>", "</html>"])
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".html", prefix="tmp", delete=False, encoding="utf-8"
    )
    path = handle.name
    handle.write("\n".join(html) + "\n")
    handle.close()
    if display:
        webbrowser.open(path)
    if clean:
        time.sleep(1)
        try:
            os.remove(path)
        except OSError:
            pass
    return path
