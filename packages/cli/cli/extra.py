"""ANSI split and wrap, HTML, palettes, hyperlinks, spinners, and keypress."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from cli.ansi_text import _AnsiState, _update_sgr, _walk, ansi_strip, ansi_substring
from cli._options import get_option, options
from cli.cat import cat_line
from cli.num_ansi_colors import num_ansi_colors
from cli.styles import (
    col_black,
    col_blue,
    col_br_black,
    col_br_blue,
    col_br_cyan,
    col_br_green,
    col_br_magenta,
    col_br_red,
    col_br_white,
    col_br_yellow,
    col_cyan,
    col_green,
    col_magenta,
    col_red,
    col_white,
    col_yellow,
)
from cli.symbol import symbol


def ansi_string(x):
    if isinstance(x, (list, tuple)):
        return ["" if item is None else str(item) for item in x]
    if x is None:
        return None
    return str(x)


def ansi_strsplit(x, split, fixed=False):
    """Split on the visible text and keep the ANSI styling of each piece."""

    values = list(x) if isinstance(x, (list, tuple)) else [x]
    pattern = "" if split is None else str(split)
    out = []
    for value in values:
        text = "" if value is None else str(value)
        plain = ansi_strip(text) or ""
        if pattern == "":
            spans = [(index, index) for index in range(1, len(plain) + 1)]
        else:
            spans = _spans(plain, pattern, fixed)
        if not spans:
            out.append([])
        else:
            out.append(ansi_substring(text, [start for start, _end in spans], [end for _start, end in spans]))
    if not isinstance(x, (list, tuple)):
        return out[0] if out else []
    return out


def _spans(plain: str, pattern: str, fixed: bool):
    if fixed:
        hits = []
        start = 0
        while True:
            at = plain.find(pattern, start)
            if at < 0:
                break
            hits.append((at, at + len(pattern)))
            start = at + max(len(pattern), 1)
    else:
        hits = [(match.start(), match.end()) for match in re.finditer(pattern, plain)]
    cuts = [0]
    for begin, end in hits:
        cuts.extend((begin, end))
    cuts.append(len(plain))
    spans = []
    for index in range(0, len(cuts) - 1, 2):
        start = cuts[index]
        stop = cuts[index + 1]
        if stop > start:
            spans.append((start + 1, stop))
    return spans


def ansi_strwrap(x, width=None, indent=0, exdent=0, simplify=True):
    """Wrap on the visible text. A plain string follows R's strwrap breaks."""

    from cli.layout import console_width

    if width is None:
        width = console_width()
    values = list(x) if isinstance(x, (list, tuple)) else [x]
    wrapped = []
    for value in values:
        text = "" if value is None else str(value)
        plain = ansi_strip(text) or ""
        lines = _wrap_plain(plain, int(width), int(indent), int(exdent))
        if plain == text:
            wrapped.append(lines)
            continue
        wrapped.append(_wrap_ansi(text, plain, lines))
    if not isinstance(x, (list, tuple)):
        if simplify:
            return wrapped[0] if wrapped else []
        return wrapped
    if simplify:
        flat = []
        for lines in wrapped:
            flat.extend(lines)
        return flat
    return wrapped


def _wrap_plain(text: str, width: int, indent: int, exdent: int) -> list[str]:
    paragraphs = re.split(r"\n[ \t\n]*\n", text)
    lines = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        first = True
        current = ""
        built = []
        for word in words:
            pad = indent if first else exdent
            if current == "":
                current = (" " * pad) + word
            elif len(current) + 1 + len(word) < width:
                current += " " + word
            else:
                built.append(current)
                first = False
                current = (" " * exdent) + word
        if current:
            built.append(current)
        lines.extend(built)
    return lines


def _wrap_ansi(text: str, plain: str, lines: list[str]) -> list[str]:
    """Map wrapped plain lines back onto the styled string, one code point at a time."""

    trimmed = [line.lstrip(" ") for line in lines]
    indents = [len(line) - len(short) for line, short in zip(lines, trimmed)]
    splits = [1]
    drop = set()
    xs = 1
    row = 0
    col = 1
    xlen = len(trimmed[0]) if trimmed else 0
    while xs <= len(plain) and row < len(trimmed):
        src = plain[xs - 1]
        dst = trimmed[row][col - 1] if col <= xlen else None
        if dst is None:
            xs += 1
        elif src == dst:
            xs += 1
            col += 1
        elif src in " \n\t":
            drop.add(xs)
            xs += 1
        elif dst == " ":
            col += 1
        else:
            xs += 1
        while row < len(trimmed) and col > xlen and xs <= len(plain) + 1:
            splits.append(xs)
            row += 1
            col = 1
            if row < len(trimmed):
                xlen = len(trimmed[row])
    splits.append(xs)
    out = []
    for index in range(len(splits) - 1):
        start = splits[index]
        stop = splits[index + 1] - 1
        while start in drop:
            start += 1
        piece = ansi_substring(text, start, max(start, stop))
        pad = indents[index] if index < len(indents) else 0
        out.append((" " * pad) + (piece or ""))
    return out


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _html_open(old, new) -> str:
    classes = []

    def add(flag, label):
        if flag:
            classes.append(label)

    add(new.bold > old.bold, "ansi-bold")
    add(new.faint > old.faint, "ansi-faint")
    add(new.italic > old.italic, "ansi-italic")
    add(new.underline > old.underline, "ansi-underline")
    add(new.blink > old.blink, "ansi-blink")
    add(new.inverse > old.inverse, "ansi-inverse")
    add(new.hide > old.hide, "ansi-hide")
    add(new.crossedout > old.crossedout, "ansi-crossedout")
    if new.fg.col and (new.fg.col != old.fg.col or new.fg.r != old.fg.r):
        if new.fg.col == 254:
            classes.append(f"ansi-color-{new.fg.r}")
        elif new.fg.col == 255:
            classes.append(f"ansi-color-{new.fg.r}-{new.fg.g}-{new.fg.b}")
        else:
            ncol = new.fg.col - 30
            if ncol > 7:
                ncol -= 60
            classes.append(f"ansi-color-{ncol}")
    if new.bg.col and (new.bg.col != old.bg.col or new.bg.r != old.bg.r):
        if new.bg.col == 254:
            classes.append(f"ansi-bg-color-{new.bg.r}")
        elif new.bg.col == 255:
            classes.append(f"ansi-bg-color-{new.bg.r}-{new.bg.g}-{new.bg.b}")
        else:
            ncol = new.bg.col - 40
            if ncol > 7:
                ncol -= 60
            classes.append(f"ansi-bg-color-{ncol}")
    if not classes:
        return ""
    return '<span class="ansi ' + " ".join(classes) + '">'


def ansi_html(x, escape_reserved=True, csi="drop"):
    values = list(x) if isinstance(x, (list, tuple)) else [x]
    out = []
    for value in values:
        if value is None:
            out.append(None)
            continue
        text = str(value)
        if escape_reserved:
            text = _html_escape(text)
        state = _AnsiState()
        parts = []
        for event in _walk(text):
            if event[0] == "sgr":
                _update_sgr(state, event[1], event[2], [])
            elif event[0] == "text":
                opening = _html_open(state.old, state.new)
                if opening:
                    parts.append(opening + event[1] + "</span>")
                else:
                    parts.append(event[1])
                state.old = state.new.clone()
            elif event[0] == "csi" and csi == "keep":
                parts.append(event[2])
        out.append("".join(parts))
    if not isinstance(x, (list, tuple)) and len(out) == 1:
        return out[0]
    return out


def _palettes() -> dict[str, list[str]]:
    path = Path(__file__).parent / "data" / "palettes.tsv"
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = {}
    for line in lines[1:]:
        name, *colors = line.split("\t")
        rows[name] = colors
    return rows


def ansi_palettes() -> dict[str, list[str]]:
    return _palettes()


def _rgb5(red: int, green: int, blue: int) -> str:
    def channel(value: int) -> int:
        return round(value / 5 * 255)

    return f"#{channel(red):02x}{channel(green):02x}{channel(blue):02x}"


def _grey(step: int) -> str:
    value = round(step / 25 * 255)
    return f"#{value:02x}{value:02x}{value:02x}"


def ansi_html_style(colors=True, palette=None):
    """CSS blocks for ansi_html(). colors=False keeps the font rules only."""

    if isinstance(colors, str):
        raise TypeError("colors must be true, false, 8, or 256")
    rows = _palettes()
    if palette is None:
        palette = "vscode"
    if isinstance(palette, str):
        if palette not in rows:
            raise ValueError(f"unknown palette {palette}")
        colors16 = rows[palette]
    else:
        colors16 = list(palette)
    ret = {
        ".ansi-bold": "{ font-weight: bold;             }",
        ".ansi-italic": "{ font-style: italic;            }",
        ".ansi-underline": "{ text-decoration: underline;    }",
        ".ansi-blink": "{ text-decoration: blink;        }",
        ".ansi-hide": "{ visibility: hidden;            }",
        ".ansi-crossedout": "{ text-decoration: line-through; }",
        ".ansi-link:hover": "{ text-decoration: underline;    }",
    }
    if colors is False:
        return ret
    for index, color in enumerate(colors16):
        ret[f".ansi-color-{index}"] = f"{{ color: {color} }}"
    for index, color in enumerate(colors16):
        ret[f".ansi-bg-color-{index}"] = f"{{ background-color: {color} }}"
    if colors is True or colors == 256:
        for blue in range(6):
            for green in range(6):
                for red in range(6):
                    number = 16 + 36 * red + 6 * green + blue
                    color = _rgb5(red, green, blue)
                    ret[f".ansi-color-{number}"] = f"{{ color: {color} }}"
        for step, number in enumerate(range(232, 256), start=1):
            ret[f".ansi-color-{number}"] = f"{{ color: {_grey(step)} }}"
        for blue in range(6):
            for green in range(6):
                for red in range(6):
                    number = 16 + 36 * red + 6 * green + blue
                    color = _rgb5(red, green, blue)
                    ret[f".ansi-bg-color-{number}"] = f"{{ background-color: {color} }}"
        for step, number in enumerate(range(232, 256), start=1):
            ret[f".ansi-bg-color-{number}"] = f"{{ background-color: {_grey(step)} }}"
    return ret


def ansi_palette_show(palette=None, colors=None, rows=4):
    if colors is None:
        colors = num_ansi_colors()
    previous = options(**{"cli.num_colors": colors})
    if palette is not None:
        options(**{"cli.palette": palette})
    block = symbol["lower_block_8"] * 4
    blocks = [
        col_black(block), col_red(block), col_green(block), col_yellow(block),
        col_blue(block), col_magenta(block), col_cyan(block), col_white(block),
        col_br_black(block), col_br_red(block), col_br_green(block), col_br_yellow(block),
        col_br_blue(block), col_br_magenta(block), col_br_cyan(block), col_br_white(block),
    ]
    names = ["blck", "red ", "grn ", "yllw", "blue", "mgnt", "cyan", "whte"] * 2

    def join(values):
        return " ".join(values[:8]) + "  " + " ".join(values[8:])

    out = [" " * 53 + "bright variants", join(names), "", *([join(blocks)] * int(rows))]
    cat_line(out)
    if previous:
        options(**previous)
    return out


def ansi_has_hyperlink_support() -> bool:
    enabled = get_option("cli.hyperlink", get_option("crayon.hyperlink"))
    if enabled is not None:
        return enabled is True
    env = os.environ.get("R_CLI_HYPERLINKS", "")
    if env.lower() == "true":
        return True
    if num_ansi_colors() == 1:
        return False
    return False


def ansi_hyperlink_types() -> dict:
    has = ansi_has_hyperlink_support()
    if not has:
        return {"href": False, "run": False, "help": False, "vignette": False}
    return {"href": True, "run": False, "help": False, "vignette": False}


def style_hyperlink(text, url, params=None) -> str:
    if isinstance(params, dict) and params:
        encoded = ":".join(f"{key}={value}" for key, value in params.items())
    else:
        encoded = ""
    end = "\x1b\\" if os.environ.get("R_CLI_HYPERLINK_MODE") == "posix" else "\x07"
    body = "" if text is None else str(text)
    if not ansi_has_hyperlink_support():
        return body
    return f"\x1b]8;{encoded};{url}{end}{body}\x1b]8;;{end}"


def _spinners() -> list[tuple[str, int, list[str]]]:
    path = Path(__file__).parent / "data" / "spinners.tsv"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        name, interval, frames = line.split("\t")
        rows.append((name, int(interval), frames.split("\x1f")))
    return rows


def list_spinners() -> list[str]:
    return [name for name, _interval, _frames in _spinners()]


def get_spinner(which=None) -> dict:
    from cli.unicode_output import is_utf8_output

    if which is None:
        if is_utf8_output():
            which = get_option("cli.spinner_unicode") or get_option("cli.spinner") or "dots"
        else:
            which = get_option("cli.spinner_ascii") or get_option("cli.spinner") or "line"
    if isinstance(which, dict):
        frames = which.get("frames")
        if not isinstance(frames, (list, tuple)) or not all(isinstance(frame, str) for frame in frames):
            raise TypeError("Spinner frames must be a character vector")
        return {
            "name": which.get("name"),
            "interval": which.get("interval") or 100,
            "frames": list(frames),
        }
    rows = {name: (interval, frames) for name, interval, frames in _spinners()}
    if which not in rows:
        raise ValueError(f"unknown spinner {which}")
    interval, frames = rows[which]
    return {"name": which, "interval": interval, "frames": frames}


class _Spinner:
    def __init__(self, spec, template, static):
        self.spec = spec
        self.template = template
        self.static = static
        self.state = 0
        self.out = []

    def spin(self):
        frame = self.spec["frames"][self.state % len(self.spec["frames"])]
        self.state += 1
        shown = self.template.replace("{spin}", frame if self.static == "print" else ".")
        if self.static == "silent":
            shown = self.template.replace("{spin}", "")
        self.out.append(shown)
        return self

    def finish(self):
        return self


def make_spinner(which=None, stream="auto", template="{spin}", static="dots"):
    if static not in ("dots", "print", "print_line", "silent"):
        raise ValueError("static must be dots, print, print_line, or silent")
    return _Spinner(get_spinner(which), template, static)


def demo_spinners(which=None):
    names = list_spinners()
    if which is None:
        chosen = names
    elif isinstance(which, str):
        chosen = [which]
    else:
        chosen = list(which)
    bad = [name for name in chosen if name not in names]
    if bad:
        raise ValueError("Unknown spinners: " + ", ".join(bad))
    for name in chosen:
        spec = get_spinner(name)
        interval = spec["interval"] / 1000
        frames = spec["frames"]
        cycles = max(round(2.5 / ((len(frames) - 1) * interval)), 1)
        for index in range(len(frames) * cycles):
            frame = frames[index % len(frames)]
            print("\r" + frame.ljust(10) + name, end="")
            time.sleep(interval)
        print()
    return None


def has_keypress_support() -> bool:
    return False


def keypress(block=True) -> str:
    if not isinstance(block, bool) or isinstance(block, bool) and block not in (True, False):
        raise ValueError("'block' must be a logical scalar")
    raise RuntimeError("Your platform/terminal does not support `keypress()`.")


def test_that_cli(desc, code, configs=("plain", "ansi", "unicode", "fancy"), links=None):
    """Run code for each requested config. The result has one entry per built-in config."""

    if isinstance(configs, str):
        configs = [configs]
    names = []
    for base in ("plain", "ansi", "unicode", "fancy"):
        names.append(base)
    for base in ("plain", "ansi", "unicode", "fancy"):
        names.append(base + "-none")
    for base in ("plain", "ansi", "unicode", "fancy"):
        names.append(base + "-all")
    results = []
    for name in names:
        if name in configs or name.split("-")[0] in configs and "-" not in name:
            if callable(code):
                code()
        results.append(None)
    return results
