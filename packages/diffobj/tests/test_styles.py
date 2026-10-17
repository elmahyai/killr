"""Style constructors against the diffobj 0.3.9 prototypes."""

import warnings

import pytest
from crayon import blue, green, options, red, yellow

from diffobj.pager import pager_is_less
from diffobj.styles import (
    AlignThreshold,
    PaletteOfStyles,
    PagerOff,
    Style,
    StyleAnsi,
    StyleAnsi256DarkRgb,
    StyleAnsi256DarkYb,
    StyleAnsi256LightRgb,
    StyleAnsi256LightYb,
    StyleAnsi8NeutralRgb,
    StyleAnsi8NeutralYb,
    StyleFuns,
    StyleHtml,
    StyleHtmlLightRgb,
    StyleHtmlLightYb,
    StyleRaw,
    StyleText,
    finalizeHtml,
    inherits,
)
from diffobj.webfiles import diffobj_css, diffobj_js


def setup_module():
    options(**{"crayon.enabled": True})


class Etc:
    def __init__(self, style):
        self.style = style


class Wrap:
    def __init__(self, style):
        self.etc = Etc(style)


def test_style_raw_classes_and_tokens():
    raw = StyleRaw()
    assert raw.classes == ("StyleRaw", "Style", "Raw")
    assert inherits(raw, "Raw")
    assert inherits(raw, "Style")
    text = raw.text
    assert text.gutter_insert == ">"
    assert getattr(text, "gutter.insert.ctd") == ":"
    assert text.gutter_delete == "<"
    assert text.gutter_match == " "
    assert text.gutter_guide == "~"
    assert getattr(text, "gutter.context.sep") == "~"
    assert text.gutter_pad == " "
    assert text.context_sep == "----------"
    assert text.pad_col == "  "
    assert text.line_break == "\n"
    assert raw.wrap is True
    assert raw.pad is True
    assert getattr(raw, "na.sub") == ""
    assert getattr(raw, "blank.sub") == ""
    assert raw.disp_width == 0
    assert raw.finalizer("obj", "kept") == "kept"
    assert raw.funs.header("z") == "z"
    if pager_is_less():
        assert raw.pager.kind == "PagerSystemLess"
        assert raw.pager.classes == ("PagerSystemLess", "PagerSystem", "Pager")
        assert raw.pager.flags == "R"
        assert raw.pager.ansi is True
    else:
        assert raw.pager.kind == "PagerSystem"
        assert raw.pager.classes == ("PagerSystem", "Pager")
        assert raw.pager.ansi is False
    assert raw.pager.threshold == -1
    assert getattr(raw.pager, "file.ext") == ""


def test_style_base_is_virtual():
    with pytest.raises(ValueError, match="virtual class"):
        Style()


def test_ansi_classes_and_colors():
    ansi = StyleAnsi()
    assert ansi.classes == ("StyleAnsi", "StyleRaw", "Ansi", "Style", "Raw")
    assert inherits(ansi, "StyleRaw")
    assert inherits(ansi, "Ansi")
    assert ansi.funs.classes == ("StyleFunsAnsi", "StyleFuns")
    assert ansi.funs.word_delete("x") == red("x")
    assert ansi.funs.word_insert("x") == green("x")
    neutral = StyleAnsi8NeutralRgb()
    assert neutral.funs.word_delete("x") == ansi.funs.word_delete("x")
    yb = StyleAnsi8NeutralYb()
    assert yb.classes[0] == "StyleAnsi8NeutralYb"
    assert "Yb" in yb.classes and "Neutral" in yb.classes
    assert yb.funs.word_insert("x") == blue("x")
    assert yb.funs.word_delete("x") == yellow("x")
    assert getattr(yb.funs, "gutter.insert")("x") == blue("x")
    assert getattr(yb.funs, "gutter.delete.ctd")("x") == yellow("x")
    assert ansi.nchar_fun is not StyleRaw().nchar_fun


def test_256_codes_match_r():
    light = StyleAnsi256LightRgb()
    assert light.funs.text_insert("x") == "\033[48;5;194mx\033[49m"
    assert light.funs.text_delete("x") == "\033[48;5;224mx\033[49m"
    assert light.funs.text_fill("x") == "\033[48;5;252mx\033[49m"
    assert light.funs.word_insert("x") == "\033[48;5;114mx\033[49m"
    assert light.funs.word_delete("x") == "\033[48;5;174mx\033[49m"
    assert light.funs.gutter_insert("x") == "\033[38;5;34mx\033[39m"
    assert light.funs.header("x") == "\033[38;5;37mx\033[39m"
    yb = StyleAnsi256LightYb()
    assert yb.funs.text_insert("x") == "\033[48;5;147mx\033[49m"
    assert yb.funs.gutter_delete("x") == "\033[38;5;94mx\033[39m"
    dark = StyleAnsi256DarkRgb()
    assert dark.funs.text_insert("x") == "\033[48;5;22mx\033[49m"
    assert dark.funs.gutter_guide("x") == "\033[38;5;245mx\033[39m"
    assert dark.funs.text_fill("x") == "\033[48;5;234mx\033[49m"
    assert dark.funs.meta("x") == "\033[38;5;245mx\033[39m"
    dyb = StyleAnsi256DarkYb()
    assert dyb.classes == (
        "StyleAnsi256DarkYb",
        "StyleAnsi",
        "Dark",
        "Yb",
        "StyleRaw",
        "Ansi",
        "Style",
        "Raw",
    )
    assert dyb.funs.word_insert("x") == "\033[48;5;21mx\033[49m"
    assert dyb.funs.word_delete("x") == "\033[48;5;136mx\033[49m"
    assert dyb.funs.text_delete("x") == "\033[48;5;58mx\033[49m"
    assert dyb.funs.trim("x") == "\033[38;5;245mx\033[39m"
    assert dyb.funs.header("x") == "\033[38;5;37mx\033[39m"


def test_palette_dimnames_and_classes():
    data = PaletteOfStyles().data
    assert data.dim == (4, 3, 2)
    assert list(data.dimnames) == ["format", "brightness", "color.mode"]
    assert data.dimnames["format"] == ("raw", "ansi8", "ansi256", "html")
    assert data.dimnames["brightness"] == ("neutral", "light", "dark")
    assert getattr(data.dimnames, "color.mode") == ("rgb", "yb")
    expected = {
        ("raw", "neutral", "rgb"): "StyleRaw",
        ("raw", "dark", "yb"): "StyleRaw",
        ("ansi8", "light", "rgb"): "StyleAnsi8NeutralRgb",
        ("ansi8", "dark", "yb"): "StyleAnsi8NeutralYb",
        ("ansi256", "neutral", "rgb"): "StyleAnsi8NeutralRgb",
        ("ansi256", "neutral", "yb"): "StyleAnsi8NeutralYb",
        ("ansi256", "light", "rgb"): "StyleAnsi256LightRgb",
        ("ansi256", "light", "yb"): "StyleAnsi256LightYb",
        ("ansi256", "dark", "rgb"): "StyleAnsi256DarkRgb",
        ("ansi256", "dark", "yb"): "StyleAnsi256DarkYb",
        ("html", "neutral", "rgb"): "StyleHtmlLightRgb",
        ("html", "dark", "yb"): "StyleHtmlLightYb",
    }
    for key, name in expected.items():
        assert data[key].__name__ == name


def test_align_threshold_defaults_and_errors():
    align = AlignThreshold()
    assert align.threshold == 0.25
    assert align.min_chars == 3
    assert getattr(align, "count.alnum.only") is True
    assert AlignThreshold(threshold=0, min_chars=1.5).min_chars == 1
    with pytest.raises(ValueError, match="threhold"):
        AlignThreshold(threshold=2)
    with pytest.raises(ValueError, match="threhold"):
        AlignThreshold(threshold=-0.1)
    with pytest.raises(ValueError, match="min.chars"):
        AlignThreshold(**{"min.chars": -1})
    with pytest.raises(ValueError, match="count.alnum.only"):
        AlignThreshold(count_alnum_only=None)


def test_style_funs_reject_non_functions():
    with pytest.raises(ValueError, match="Argument `container` should be a function"):
        StyleFuns(container=1)
    def bad(x, y):
        return y
    with pytest.raises(ValueError, match="non-default formals"):
        StyleFuns(**{"word.insert": bad})
    assert StyleFuns(container=lambda: 1).container() == 1


def test_style_validity_messages():
    with pytest.raises(ValueError, match="disp.width"):
        StyleRaw(disp_width=-1)
    with pytest.raises(ValueError, match="Slot `na.sub` must be character"):
        StyleRaw(**{"blank.sub": ["a", "b"]})
    with pytest.raises(ValueError, match="wrap"):
        StyleRaw(wrap=None)
    with pytest.raises(ValueError, match="at least two parameters"):
        StyleRaw(finalizer=lambda x: x)
    with pytest.raises(ValueError, match="no non-default parameters"):
        StyleRaw(finalizer=lambda x, y, z: z)


def test_html_defaults_and_light_containers():
    html = StyleHtml()
    assert html.classes == ("StyleHtml", "Style", "Html")
    assert html.html_output == "auto"
    assert html.css == diffobj_css()
    assert html.js == diffobj_js()
    assert html.scale is True
    assert html.wrap is False
    assert html.pad is False
    assert getattr(html, "na.sub") == "&nbsp;"
    assert html.disp_width == 80
    assert getattr(html, "escape.html.entities") is True
    assert html.pager.kind == "PagerBrowser"
    assert html.finalizer is finalizeHtml
    assert html.text.gutter_insert == "&gt;"
    assert html.text.gutter_delete == "&lt;"
    assert html.text.gutter_match == "&nbsp;"
    assert html.text.line_break == "<br />"
    assert html.text.pad_col == ""
    assert html.text.gutter_insert_ctd == ":"
    body = "<div class='diffobj-container'><pre class='diffobj-content'>BODY</pre></div>"
    assert html.funs.container("BODY") == body
    assert html.funs.gutter_insert(">") == "<div class='insert'>></div>"
    assert getattr(html.funs, "gutter.context.sep")("~") == "<div class='context_sep ctd'>~</div>"
    assert html.funs.word_insert("w") == "<span class='diffobj-word insert'>w</span>"
    assert html.funs.header("h") == "<div class='diffobj-header'>h</div>"
    rgb = StyleHtmlLightRgb()
    assert rgb.classes == ("StyleHtmlLightRgb", "StyleHtml", "Light", "Rgb", "Style", "Html")
    assert rgb.funs.container("BODY") == (
        "<div class='diffobj-container light rgb'>"
        "<pre class='diffobj-content'>BODY</pre></div>"
    )
    yb = StyleHtmlLightYb()
    assert yb.funs.container("BODY") == (
        "<div class='diffobj-container light yb'>"
        "<pre class='diffobj-content'>BODY</pre></div>"
    )
    assert StyleHtml(escape_html_entities=False).escape_html_entities is True
    with pytest.raises(ValueError, match="diff.w.style"):
        StyleHtml(**{"html.output": "nope"})
    with pytest.raises(ValueError, match="styleHtml"):
        StyleHtml(wrap=True)
    with pytest.raises(ValueError, match="not a file"):
        StyleHtml(css="nope")


def test_summary_text():
    summary = StyleRaw().summary
    assert summary.container(["a", "b"]) == "\nab\n"
    assert summary.detail(["a", "b"]) == "\n  a  b\n"
    assert summary.map(["a", "b"]) == "\n  a\n  b"
    assert StyleHtml().summary.container(["a", "b"]) == "<div class='diffobj-summary'>ab</div>"
    assert StyleHtml().summary.classes == ("StyleSummaryHtml", "StyleSummary")


def test_finalize_html_modes():
    only = StyleHtml(**{"html.output": "diff.only"})
    assert finalizeHtml(Wrap(only), ["aa", "bb"], "") == "aabb"
    styled = StyleHtml(**{"html.output": "diff.w.style"})
    wrapped = finalizeHtml(Wrap(styled), "zz", "")
    assert wrapped.startswith("<style type='text/css'>\n")
    assert wrapped.endswith("</style>zz")
    page = finalizeHtml(Wrap(StyleHtml(**{"html.output": "page"})), ["aa", "bb"], "alert(1)")
    assert page.startswith("\n        <!DOCTYPE html>\n")
    assert "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"/>" in page
    assert "<div id='diffobj_outer'>\naabb\n</div>" in page
    assert "<script type='text/javascript'>\nalert(1)\n</script>" in page
    auto = finalizeHtml(Wrap(StyleHtml()), "qq", "ok")
    assert auto.startswith("\n        <!DOCTYPE html>\n")
    assert "qq" in auto
    off = StyleHtml(**{"html.output": "auto", "pager": PagerOff()})
    assert finalizeHtml(Wrap(off), "qq", "ok") == "qq"
    broken = StyleHtml()
    broken.css = "/no/such/diffobj.css"
    broken.html_output = "diff.w.style"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = finalizeHtml(Wrap(broken), "z", "")
    assert result == "z"
    assert any("cannot open the connection" in str(item.message) for item in caught)
    with pytest.raises(TypeError, match="x.chr"):
        finalizeHtml(Wrap(only), 1, "a")
    with pytest.raises(TypeError, match="js"):
        finalizeHtml(Wrap(only), "a", 1)


def test_dotted_and_snake_kwargs():
    text = StyleText(**{"gutter.insert": "+++"})
    assert text.gutter_insert == "+++"
    assert getattr(text, "gutter.insert") == "+++"
    style = StyleRaw(**{"na.sub": "NA", "disp.width": 10})
    assert getattr(style, "na.sub") == "NA"
    assert style.disp_width == 10
