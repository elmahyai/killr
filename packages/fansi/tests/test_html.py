"""HTML conversion checks against the strings installed fansi 1.0.7 returned."""

import io
import contextlib

import pytest

from fansi._args import FansiError
from fansi.html_esc import html_esc
from fansi.make_styles import make_styles
from fansi.set_knit_hooks import set_knit_hooks
from fansi.to_html import sgr_to_html, to_html


def test_to_html_basic_and_carry():
    assert to_html("hello\033[31;42;1mworld\033[m", warn=False) == [
        "hello<span style='color: #BB0000; background-color: #00BB00; font-weight: bold;'>world</span>"
    ]
    assert to_html(["\033[31mhello", "world"], warn=False) == [
        "<span style='color: #BB0000;'>hello</span>",
        "<span style='color: #BB0000;'>world</span>",
    ]
    assert to_html(["\033[31mhello", "world"], warn=False, carry=False) == [
        "<span style='color: #BB0000;'>hello</span>",
        "world",
    ]
    assert to_html(["A\033[44m", None, "C"], warn=False) == ["A", None, None]
    assert sgr_to_html(["hello\033[33m", "world"], warn=False) == [
        "hello",
        "<span style='color: #BBBB00;'>world</span>",
    ]


def test_classes_and_links():
    html = to_html("\033[94mhello\033[31;42;1mworld\033[m", classes=True, warn=False)
    assert html == [
        "<span class='fansi-color-012'>hello</span>"
        "<span class='fansi-color-001 fansi-bgcol-002' style='font-weight: bold;'>world</span>"
    ]
    assert to_html("\033]8;id=a;http://ex\033\\hello\033[m world", warn=False) == [
        "<a href='http://ex'>hello world</a>"
    ]
    assert to_html("\033]8;;http://ex\033\\hello\033[m world", warn=False) == [
        "<a href='http://ex'>hello</a><a href='http://ex'> world</a>"
    ]


def test_html_esc_and_styles():
    assert html_esc("<a & b>") == ["&lt;a &amp; b&gt;"]
    assert html_esc("say 'hi'") == ["say &#039;hi&#039;"]
    assert html_esc(["h&e'l\"lo", None], "<>") == ["h&e'l\"lo", None]
    names = [f"{side}-{index}" for index in range(8) for side in ("fg", "bg")]
    rules = make_styles(names)
    assert rules[:2] == [
        ".fg-0 {color: #000000;}",
        ".bg-0 {background-color: #000000;}",
    ]
    mix = [[0.6, 0.2, 0.2], [0.2, 0.6, 0.2], [0.2, 0.2, 0.6]]
    assert make_styles(names, mix)[2] == ".fg-1 {color: #4C1919;}"
    with pytest.raises(FansiError, match="length 16, 32, or 512"):
        make_styles(["a", "b"])


class _Hooks:
    def __init__(self):
        self.names = []

    def get(self, name):
        return lambda x, options: "old-output"

    def set(self, **kwargs):
        self.names.extend(kwargs)
        return None


def test_set_knit_hooks():
    hooks = _Hooks()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        old = set_knit_hooks(hooks)
    assert hooks.names == ["output"]
    assert old["output"]("z", None) == "old-output"
    assert buf.getvalue() == (
        "<STYLE type='text/css' scoped>\n"
        "PRE.fansi SPAN {padding-top: .25em; padding-bottom: .25em};\n"
        "</STYLE>\n"
    )
    fresh = _Hooks()
    with contextlib.redirect_stdout(io.StringIO()):
        probed = set_knit_hooks(fresh, _test=True)
    rendered = probed["new.hooks"]["output"]("hello\033[31m world", None)
    assert rendered == (
        '<PRE class="fansi fansi-output"><CODE>'
        "hello<span style='color: #BB0000;'> world</span>"
        "</CODE></PRE>"
    )
