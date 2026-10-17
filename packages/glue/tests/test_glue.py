import datetime

import pytest

from glue import (
    Id,
    NA,
    SQL,
    as_glue,
    backtick,
    double_quote,
    glue,
    glue_col,
    glue_collapse,
    glue_data,
    glue_data_col,
    glue_data_safe,
    glue_data_sql,
    glue_safe,
    glue_sql,
    glue_sql_collapse,
    identity_transformer,
    single_quote,
    sqlite,
    trim,
)
from glue._scan import GlueError


def test_glue_evaluates_python_expressions():
    assert glue("My name is {name}, my age next year is {age + 1}.", name="Fred", age=50) == (
        "My name is Fred, my age next year is 51."
    )


def test_doubled_braces_are_literals():
    assert glue("My name is {name}, not {{name}}.", name="Fred") == "My name is Fred, not {name}."


def test_custom_delimiters_and_dotted_names():
    assert glue("The value is <<one>>.", open="<<", close=">>", one="1") == "The value is 1."
    result = glue_data(
        {"Species": ["setosa", "versicolor"], "Petal.Length": [1.4, 4.7]},
        "This {Species} has a petal length of {Petal.Length}",
    )
    assert list(result.values) == [
        "This setosa has a petal length of 1.4",
        "This versicolor has a petal length of 4.7",
    ]


def test_glue_safe_does_not_evaluate():
    assert glue_safe("{1 + 1}", **{"1 + 1": 5}) == "5"
    with pytest.raises(GlueError, match="not found"):
        glue_safe("{1 + 1}", envir={})


def test_glue_data_safe_looks_up_columns():
    assert glue_data_safe({"name": "Fred"}, "{name}", envir={}) == "Fred"


def test_collapse_and_width():
    assert glue_collapse([1, 2, 3, 4], ", ", last=" and ") == "1, 2, 3 and 4"
    assert glue_collapse("12345678910", width=5) == "12..."
    assert glue_collapse([]) == ""
    assert glue_collapse(["a", NA]) is not None
    assert glue_collapse(["a", NA]).values == (NA,)


def test_trim_matches_the_manual_shapes():
    assert trim(
        "\n    A formatted string\n    Can have multiple lines\n      with additional indentation preserved\n    "
    ) == "A formatted string\nCan have multiple lines\n  with additional indentation preserved"
    assert (
        trim("\n  \ntrailing or leading newlines can be added explicitly\n\n  ")
        == "  \ntrailing or leading newlines can be added explicitly\n"
    )
    assert (
        trim("\n    A formatted string \\\n    can also be on a \\\n    single line\n    ")
        == "A formatted string can also be on a single line"
    )
    assert trim("no newline") == "no newline"


def test_quotes():
    assert list(single_quote([1, 2, 3, 4, 5]).values) == ["'1'", "'2'", "'3'", "'4'", "'5'"]
    assert single_quote(NA).values == (NA,)
    assert single_quote("") == "''"
    assert single_quote("b'c") == "'b\\'c'"
    assert double_quote("b'c") == "\"b'c\""
    assert backtick("a") == "`a`"
    assert list(single_quote([]).values) == []


def test_as_glue_and_addition():
    made = as_glue(["abc", '"\\', "\n"])
    assert list(made.values) == ["abc", '"\\', "\n"]
    assert as_glue("abc") + "def" == "abcdef"


def test_identity_transformer():
    assert identity_transformer("age + 1", {"age": 50}) == 51


def test_color_codes():
    assert glue_col("{blue foo}", envir={}) == "\033[34mfoo\033[39m"
    assert glue_col("{red This is a {green serious} problem}", envir={}) == (
        "\033[31mThis is a \033[32mserious\033[31m problem\033[39m"
    )
    colored = glue_data_col({"gear": [3, 4]}, "A {blue {gear}}", envir={})
    assert list(colored.values) == [
        "A \033[34m3\033[39m",
        "A \033[34m4\033[39m",
    ]


def test_sql_quotes_like_rsqlite():
    query = glue_sql(
        "SELECT {var} FROM {`tbl`} WHERE species IN ({vals*})",
        con=sqlite,
        var="setosa",
        tbl="iris",
        vals=["setosa", "versicolor"],
        envir={},
    )
    assert query == "SELECT 'setosa' FROM `iris` WHERE species IN ('setosa', 'versicolor')"
    assert glue_sql("{var}", con=sqlite, var=1, envir={}) == "1"
    assert glue_sql("{var*}", con=sqlite, var=[], envir={}) == "NULL"
    assert glue_sql("{`var`}", con=sqlite, var=Id(schema="foo", table="bar", column="baz"), envir={}) == (
        "`foo`.`bar`.`baz`"
    )
    assert glue_sql("x = {var}", con=sqlite, var=datetime.date(2019, 1, 1), envir={}) == "x = '2019-01-01'"
    assert isinstance(query, SQL)
    with pytest.raises(GlueError, match="absent"):
        glue_sql("{var}", var="a")


def test_glue_data_sql_and_collapse():
    quoted = glue_data_sql({"name": "O'Malley"}, "INSERT {name}", con=sqlite, envir={})
    assert quoted == "INSERT 'O''Malley'"
    assert glue_sql_collapse(["a", "b"], sep=", ") == "a, b"
    assert isinstance(glue_sql_collapse(["a", "b"]), SQL)


def test_unterminated_brace():
    with pytest.raises(GlueError, match="Expecting"):
        glue("x={x", envir={})
