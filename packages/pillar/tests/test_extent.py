"""Extent, alignment, and ornaments against pillar 1.11.1."""

import math

from cli import options as cli_options
from pillar._color import bold
from pillar._options import get_option, set_option
from pillar.extent import align, get_extent, get_max_extent, new_ornament


def test_get_extent_widths():
    assert get_extent(["abc", "de"]) == [3, 2]
    assert get_extent("運氣") == 4
    assert get_extent("\033[31mabc\033[39m") == 3
    assert get_extent("a\tb") == 2
    assert get_extent(None) == 2
    assert get_extent(["a", None]) == [1, 2]
    assert get_extent([]) == []
    assert get_extent("\033]8;;http://x\007abc") == 3


def test_get_max_extent():
    assert get_max_extent(["abc", "de"]) == 3
    assert get_max_extent([]) == 0
    assert get_max_extent(None) == 2
    assert get_max_extent("運氣") == 4


def test_align_sides_and_prefixes():
    assert align(["abc", "de"], align="left") == ["abc", "de "]
    assert align(["abc", "de"], align="right") == ["abc", " de"]
    assert align(["abc", "de"], align="l") == ["abc", "de "]
    assert align(["abc", "de"], align="r") == ["abc", " de"]
    assert align(["abc", "de"], align=None) == ["abc", "de "]
    assert align(["abc", "de"]) == ["abc", "de "]


def test_align_missing_and_space():
    assert align(["a", None], align="left") == ["a ", "NA"]
    assert align(["a", None], align="right") == [" a", "NA"]
    assert align(["a", "bb"], space="ab") == ["aab", "bb"]
    assert align("x", width=3, space="ab") == "xabab"
    assert align(["abc", "de"], width=1) == ["abc", "de"]
    assert align(["ab", "c"], width=3.9, align="right") == [" ab", "  c"]
    assert align(["abc", "de"], width=float("inf")) == ["abcNA", "deNA"]
    assert align(["ab"], width=-3) == ["ab"]
    assert align([]) == []
    assert align(None) == "NA"


def test_align_rejects_unknown():
    try:
        align(["a"], align="nope")
    except ValueError as exc:
        assert "should be one of" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_new_ornament_print_and_format():
    ornament = new_ornament(["abc", "de"], align="right")
    assert ornament.align == "right"
    assert ornament.width == 3
    assert str(ornament) == "<pillar_ornament>\nabc\n de"
    assert ornament.format() == ["abc", " de"]
    assert ornament.format(width=5) == ["  abc", "   de"]
    plain = new_ornament(["abc", "de"])
    assert plain.align is None
    assert plain.format() == ["abc", "de "]
    wide = new_ornament(["abc", "de"], width=5.9, align="right")
    assert wide.width == 5
    assert str(wide) == "<pillar_ornament>\n  abc\n   de"
    empty = new_ornament([])
    assert empty.width == 0
    assert str(empty) == "<pillar_ornament>"
    prefix = new_ornament(["abc", "de"], align="r")
    assert prefix.align == "r"
    assert prefix.format() == ["abc", " de"]


def test_new_ornament_infinite_width():
    ornament = new_ornament(["abc", "de"], width=float("inf"))
    assert math.isnan(ornament.width)
    assert ornament.format() == ["abcNA", "deNA"]


def test_ornament_bold_follows_the_option():
    previous_colors = cli_options(**{"cli.num_colors": 16})
    previous_bold = get_option("pillar.bold")
    try:
        set_option("pillar.bold", False)
        plain = str(new_ornament(["abc", "de"], align="right"))
        assert plain == "<pillar_ornament>\nabc\n de"
        assert "\033" not in plain
        set_option("pillar.bold", True)
        colored = str(new_ornament(["abc", "de"], align="right"))
        header = bold("<pillar_ornament>")
        assert colored.startswith(header + "\n")
        assert header == "\033[1m<pillar_ornament>\033[22m"
        assert colored.endswith("\nabc\n de")
    finally:
        set_option("pillar.bold", previous_bold)
        cli_options(**previous_colors)
