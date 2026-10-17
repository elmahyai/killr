"""Checks that do not need R. The proof scripts are the R comparison."""

from datetime import date, datetime

from cli._options import options as cli_options

from pillar._options import options as pillar_options
from pillar._vec import (
    NULL,
    DataFrame,
    Environment,
    Factor,
    List,
    Matrix,
    Table,
)
from pillar.summary import dim_desc, obj_sum, size_sum, tbl_sum, type_sum


def setup_module() -> None:
    cli_options(**{"cli.unicode": True})


class _Vec(list):
    pass


def test_dim_desc_length_and_shape():
    assert dim_desc(list(range(1, 11))) == "10"
    assert dim_desc(Table((4, 2, 2, 2))) == "4 × 2 × 2 × 2"
    assert dim_desc(NULL) == "0"
    assert dim_desc([]) == "0"
    assert dim_desc(1) == "1"
    assert dim_desc(Matrix(list(range(1, 11)), 10)) == "10 × 1"
    assert dim_desc(Matrix(list(range(1, 5)), 2)) == "2 × 2"
    assert dim_desc(DataFrame({"a": [1]})) == "1 × 1"
    trees = DataFrame({name: list(range(31)) for name in ("Girth", "Height", "Volume")})
    assert dim_desc(trees) == "31 × 3"
    assert dim_desc(list(range(1000))) == "1,000"
    wide = _Vec([0])
    wide.dim = (1000000, 2000)
    assert dim_desc(wide) == "1,000,000 × 2,000"
    missing = _Vec([1, 2, 3, 4])
    missing.dim = (None, 2)
    assert dim_desc(missing) == "?? × 2"


def test_dim_desc_outdec_and_ascii_times():
    previous = pillar_options(**{"OutDec": ","})
    try:
        assert dim_desc(list(range(1000))) == "1.000"
        assert dim_desc(Table((4, 2, 2, 2))) == "4 × 2 × 2 × 2"
        boxed = _Vec([0])
        boxed.dim = (1000, 2000)
        assert dim_desc(boxed) == "1.000 × 2.000"
    finally:
        pillar_options(**previous)
    cli_options(**{"cli.unicode": False})
    try:
        assert dim_desc(Table((4, 2, 2, 2))) == "4 x 2 x 2 x 2"
    finally:
        cli_options(**{"cli.unicode": True})


def test_type_sum_names():
    assert type_sum(Factor(["a", "b", "c"])) == "fct"
    assert type_sum(Factor(["a", "b"], ordered=True)) == "ord"
    assert type_sum(list(range(1, 11))) == "int"
    assert type_sum(1.5) == "dbl"
    assert type_sum(True) == "lgl"
    assert type_sum("a") == "chr"
    assert type_sum(1 + 2j) == "cpl"
    assert type_sum([1 + 2j]) == "cpl"
    assert type_sum(b"\x01") == "raw"
    assert type_sum(DataFrame({"a": [1]})) == "df[,1]"
    assert type_sum(DataFrame({})) == "df[,0]"
    assert type_sum(Matrix(list(range(1, 5)), 2)) == "int[,2]"
    assert type_sum(Matrix(list(range(1, 11)), 10)) == "int[,1]"
    assert type_sum(Table((4, 2, 2, 2))) == "table[,2,2,2]"
    assert type_sum(Table((2,))) == "table[1d]"
    assert type_sum(date.today()) == "date"
    assert type_sum(datetime.now()) == "dttm"
    assert type_sum(List([1, 2])) == "list"
    assert type_sum([1, 2]) == "int"
    assert type_sum(len) == "fn"
    assert type_sum(Environment()) == "env"
    assert type_sum(NULL) == "NULL"
    flat = _Vec(list(range(1, 11)))
    flat.dim = (10,)
    assert type_sum(flat) == "int[1d]"
    labeled = Factor(["a"], ordered=True)
    labeled.pillar = {"label": "LAB"}
    assert type_sum(labeled) == "LAB"
    plain = Factor(["a"])
    plain.pillar = {"label": "LAB"}
    assert type_sum(plain) == "fct"


def test_obj_sum_text_and_short():
    vector = obj_sum(list(range(1, 11)))
    assert vector == "int [10]"
    assert vector.short == "int"
    matrix = obj_sum(Matrix(list(range(1, 11)), 10))
    assert matrix == "int [10 × 1]"
    assert matrix.short == "int[…]"
    frame = obj_sum(DataFrame({"a": [1]}))
    assert frame == "df [1 × 1]"
    assert frame.short == "df"
    assert obj_sum(date.today()) == "date [1]"
    assert obj_sum(date.today()).short == "date"
    clock = obj_sum(datetime.now())
    assert clock == "dttm [1]"
    assert clock.short == "dttm"
    function = obj_sum(len)
    assert function == "fn"
    assert not hasattr(function, "short")
    assert obj_sum(NULL) == "NULL"
    assert not hasattr(obj_sum(NULL), "short")
    assert obj_sum(Environment()) == "env"
    listed = obj_sum(List([1, 2]))
    assert listed == "list [2]"
    assert listed.short == "list"
    atomic = obj_sum([1, 2])
    assert atomic == "int [2]"
    assert atomic.short == "int"
    table = obj_sum(Table((4, 2, 2, 2)))
    assert table == "table [4 × 2 × 2 × 2]"
    assert table.short == "table[…]"
    flat = _Vec(list(range(1, 11)))
    flat.dim = (10,)
    one_d = obj_sum(flat)
    assert one_d == "int [10]"
    assert one_d.short == "int[…]"
    assert obj_sum(1) == "int [1]"
    assert obj_sum(1).short == "int"


def test_obj_sum_ascii_ellipsis():
    cli_options(**{"cli.unicode": False})
    try:
        matrix = obj_sum(Matrix(list(range(1, 11)), 10))
        assert matrix == "int [10 x 1]"
        assert matrix.short == "int[...]"
    finally:
        cli_options(**{"cli.unicode": True})


def test_size_sum():
    trees = DataFrame({name: list(range(31)) for name in ("Girth", "Height", "Volume")})
    assert size_sum(list(range(1, 11))) == "[10]"
    assert size_sum(trees) == "[31 × 3]"
    assert size_sum(Table((4, 2, 2, 2))) == "[4 × 2 × 2 × 2]"
    assert size_sum(1) == "[1]"
    assert size_sum(len) == ""
    assert size_sum(NULL) == ""
    assert size_sum(Environment()) == ""
    assert size_sum(DataFrame({"a": [1]})) == "[1 × 1]"
    assert size_sum(date.today()) == "[1]"


def test_tbl_sum_is_the_default_description():
    vector = tbl_sum(list(range(1, 11)))
    assert str(vector) == "int [10]"
    assert vector.name == "Description"
    assert not hasattr(vector, "short")
    frame = DataFrame({"a": [1]})
    described = tbl_sum(frame)
    assert str(described) == "df [1 × 1]"
    assert described.name == "Description"
    assert str(described) == str(obj_sum(frame))
    assert described.name != "A data frame"
    assert str(tbl_sum(len)) == "fn"
    assert tbl_sum(len).name == "Description"
    assert str(tbl_sum(Matrix(list(range(1, 11)), 10))) == "int [10 × 1]"
    assert str(tbl_sum(date.today())) == "date [1]"
    assert str(tbl_sum(datetime.now())) == "dttm [1]"
