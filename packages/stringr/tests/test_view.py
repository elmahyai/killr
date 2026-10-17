"""Checks for the stringr view, glue wrappers, interpolator, and pipe."""

import warnings

import pytest

from cli._options import set_option
from stringi._na import NA
from stringr.glue import str_glue, str_glue_data
from stringr.interp import str_interp
from stringr.pattern import boundary, coll, fixed
from stringr.pipe import pipe
from stringr.view import str_view, str_view_all


set_option("cli.num_colors", 1)


def test_str_glue_name_age_and_doubled_braces():
    name = "Fred"
    age = 50
    anniversary = "Saturday, October 12, 1991"
    assert str_glue(
        "My name is {name}, ",
        "my age next year is {age + 1}, ",
        "and my anniversary is {anniversary}.",
    ) == ["My name is Fred, my age next year is 51, and my anniversary is Saturday, October 12, 1991."]
    assert str_glue("My name is {name}, not {{name}}.") == ["My name is Fred, not {name}."]
    assert str_glue(
        "My name is {name}, and my age next year is {age + 1}.",
        name="Joe",
        age=40,
    ) == ["My name is Joe, and my age next year is 41."]


def test_str_glue_data():
    data = {"name": ["Mazda RX4", "Datsun 710"], "hp": [110, 93]}
    assert str_glue_data(data, "{name} has {hp} hp") == [
        "Mazda RX4 has 110 hp",
        "Datsun 710 has 93 hp",
    ]


def test_str_interp_list_format_and_collapse():
    assert str_interp(
        "One value, ${value1}, and then another, ${value2*2}.",
        {"value1": 10, "value2": 20},
    ) == ["One value, 10, and then another, 40."]
    assert str_interp(
        "User ${user_name} (account $[08d]{account}) has $$[.2f]{amount}.",
        {"user_name": "smbache", "account": 1337, "amount": 6.656},
    ) == ["User smbache (account 00001337) has $6.66."]
    assert str_interp(
        [
            "This particular line is so long that it is hard to write ",
            "without breaking the ${max_char}-char barrier!",
        ],
        {"max_char": 80},
    ) == ["This particular line is so long that it is hard to write without breaking the 80-char barrier!"]
    with pytest.raises(ValueError, match="Invalid template"):
        str_interp("${${msg}}")


def test_pipe_is_magrittr():
    assert pipe(2, lambda value: value + 3, lambda value: value * 4) == 20


def test_str_view_matches_and_filter():
    viewed = str_view(["abc", "def", "fghi"], "[aeiou]")
    assert list(viewed) == ["<a>bc", "d<e>f", "fgh<i>"]
    assert viewed.ids == [1, 2, 3]
    assert viewed.spans == [[[1, 1]], [[2, 2]], [[4, 4]]]

    missed = str_view(["abc", "def", "fghi"], "e", match=False)
    assert list(missed) == ["abc", "fghi"]
    assert missed.ids == [1, 3]

    assert list(str_view(["abc", "def", "fghi"], "^")) == ["<>abc", "<>def", "<>fghi"]
    assert list(str_view(["abc", "def", "fghi"], "..")) == ["<ab>c", "<de>f", "<fg><hi>"]
    assert str_view("a\nb\nbbb\nc", "(b|\n)+").spans == [[[2, 8]]]

    kept = str_view(["abc", "def", "fgh", NA], "d|e", match=NA)
    assert kept.ids == [1, 2, 3, 4]
    assert kept[3] is NA
    assert str_view(["abc", "def", "fgh", NA], "d|e").ids == [2]
    assert str_view(["abc", "def", "fgh", NA], "d|e", match=False).ids == [1, 3, 4]


def test_str_view_whitespace_escapes_and_engines():
    assert list(str_view("Hi\u00A0you")) == ["Hi{\\u00a0}you"]
    assert list(str_view("Hi\u00A0you", use_escapes=True)) == ["Hi\\u00a0you"]
    assert list(str_view([" ", "\u00A0", "\n", "\t"], use_escapes=True)) == [" ", "\\u00a0", "\\n", "\\t"]
    assert list(str_view(["ab", "ba"], fixed("a"))) == ["<a>b", "b<a>"]
    assert list(str_view(["A", "b"], coll("a", ignore_case=True))) == ["<A>"]
    assert list(str_view("ab", boundary("character"))) == ["<a><b>"]
    assert str_view(["ab", "a", "b"], fixed("a")).ids == [1, 2]


def test_str_view_all_warns_and_html_is_unavailable():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        viewed = str_view_all(["abc", "def", "fghi"], "e")
    assert "str_view_all()" in str(caught[0].message)
    assert "str_view()" in str(caught[0].message)
    assert list(viewed) == ["abc", "d<e>f", "fghi"]
    assert viewed.ids == [1, 2, 3]
    with pytest.raises(RuntimeError, match="htmltools"):
        str_view("abc", "a", html=True)
    with pytest.raises(ValueError, match="empty string"):
        str_view("a", "")
