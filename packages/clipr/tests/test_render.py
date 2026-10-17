"""Rendering checks that do not need the clipboard."""

from __future__ import annotations

import math

import pytest

from clipr._render import Frame, Matrix, make_names, r_character_double, render_object


def _render(content, breaks="\n", **dots):
    if "sep" not in dots:
        dots["sep"] = "\t"
    return render_object(content, "auto", breaks, dots)


def test_character_lines():
    assert _render("hello, world!") == "hello, world!"
    assert _render(["hello", "world!"]) == "hello\nworld!"
    assert _render(["hello", "world!"], breaks=", ") == "hello, world!"
    assert _render("") == ""


def test_single_na_renders_as_na():
    with pytest.warns(UserWarning, match="Coercing"):
        assert _render(float("nan")) == "NA"


def test_default_frame():
    rendered = _render({"a": [1, 2, 3], "b": [4, 5, 6]})
    assert rendered == "a\tb\n1\t4\n2\t5\n3\t6"


def test_frame_custom_separator():
    rendered = _render({"a": [1, 2, 3], "b": [4, 5, 6]}, sep=",")
    assert rendered == "a,b\n1,4\n2,5\n3,6"


def test_matrix_without_names():
    rendered = _render([[1, 4], [2, 5], [3, 6]])
    assert rendered == "1\t4\n2\t5\n3\t6"


def test_names_add_a_leading_separator():
    table = Matrix([[1, 3], [2, 4]], row_names=["a", "b"], col_names=["c", "d"])
    assert _render(table) == "\tc\td\na\t1\t3\nb\t2\t4"
    frame = Frame({"c": [1, 2], "d": [3, 4]}, row_names=["a", "b"])
    assert _render(frame) == "\tc\td\na\t1\t3\nb\t2\t4"


def test_row_names_without_column_names():
    frame = Frame({"c": [1, 2], "d": [3, 4]}, row_names=["a", "b"])
    rendered = _render(frame, **{"row.names": True, "col.names": False})
    assert rendered == "a\t1\t3\nb\t2\t4"


def test_double_formatting_matches_known_r_results():
    expected = {
        1e-5: "1e-05",
        1e-4: "1e-04",
        0.001: "0.001",
        0.00012: "0.00012",
        999999: "999999",
        100000: "1e+05",
        1e6: "1e+06",
        1 / 3: "0.333333333333333",
        math.pi: "3.14159265358979",
        1.2345678901234567: "1.23456789012346",
        0.000999: "0.000999",
        10.10: "10.1",
        2.875: "2.875",
        16.46: "16.46",
        6.0: "6",
        0.0: "0",
        -2.5: "-2.5",
        0.2: "0.2",
        4.9: "4.9",
        5.1: "5.1",
        3.5: "3.5",
    }
    for value, text in expected.items():
        assert r_character_double(value) == text


def test_make_names():
    assert make_names(["Name's", "1abc", "a b", "a", "a", ""], unique=True) == [
        "Name.s",
        "X1abc",
        "a.b",
        "a",
        "a.1",
        "X",
    ]
    assert make_names(["NA", "TRUE"], unique=True) == ["NA.", "TRUE."]
