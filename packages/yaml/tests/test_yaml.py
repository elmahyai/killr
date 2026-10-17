"""Checks against the behavior of CRAN yaml 2.3.12."""

import warnings
from pathlib import Path

import pytest

from r_yaml import as_yaml, read_yaml, verbatim_logical, write_yaml, yaml_load, yaml_load_file
from r_yaml.load import YamlError
from r_yaml.types import NA_INTEGER, NA_REAL, Quoted, Vector


def test_as_yaml_named_vectors():
    text = as_yaml(
        {
            "foo": Vector(list(range(1, 11)), "integer"),
            "bar": Vector(["test1", "test2"], "character"),
        }
    )
    assert text == (
        "foo:\n- 1\n- 2\n- 3\n- 4\n- 5\n- 6\n- 7\n- 8\n- 9\n- 10\n"
        "bar:\n- test1\n- test2\n"
    )


def test_as_yaml_yes_no_and_quoting():
    assert as_yaml(True) == "yes\n"
    assert as_yaml(False) == "no\n"
    assert as_yaml("12345") == "'12345'\n"
    assert as_yaml(None) == "~\n"
    assert as_yaml({"ports": [Quoted("80:80")]}) == 'ports:\n- "80:80"\n'


def test_yaml_load_yes_and_sexagesimal():
    value = yaml_load("flag: y\nclock: 1:20\n")
    assert value["flag"] is True
    assert value["clock"] == "1:20"
    assert yaml_load("015") == 13
    assert yaml_load("'yes'") == "yes"
    assert yaml_load("!!str y") == "y"


def test_yaml_load_missing_and_overflow():
    with pytest.warns(UserWarning, match="not an integer"):
        assert yaml_load("!!int 1:20") == NA_INTEGER
    with pytest.warns(UserWarning, match="out of integer range"):
        assert yaml_load("2147483648") == NA_INTEGER
    with pytest.warns(UserWarning, match="out of real range"):
        assert yaml_load("1.797693e+309") == NA_REAL


def test_yaml_load_merge_order_and_override():
    text = "base: &a\n  x: 1\n  p: 2\nitem:\n  p: 3\n  <<: *a\n  z: 4\n"
    ordered = yaml_load(text)
    assert ordered["item"] == {"p": 3, "x": 1, "z": 4}
    overridden = yaml_load(text, merge_precedence="override")
    assert list(overridden["item"]) == ["p", "z", "x"]
    with pytest.warns(UserWarning, match="during merge"):
        kept = yaml_load("a: &m {x: 1}\nb:\n  x: 9\n  <<: *m", merge_warning=True)
    assert kept["b"]["x"] == 9


def test_yaml_load_errors_and_handlers():
    with pytest.raises(YamlError, match="Duplicate map key: 'foo'"):
        yaml_load("foo: 1\nfoo: 2")
    with pytest.raises(YamlError, match="Illegal merge: 1"):
        yaml_load("<<: 1")
    with pytest.raises(YamlError, match="Duplicate omap key: 'a'"):
        yaml_load("!!omap\n- a: 1\n- a: 2")
    with pytest.raises(YamlError, match="Invalid tag: str for sequence"):
        yaml_load("!!str [a, b]")
    with pytest.warns(UserWarning, match="using default handler"):
        assert yaml_load("!!int 7", handlers={"int": _fail}) == 7
    assert yaml_load("!!int 7", handlers={"int": lambda text: f"n={text}"}) == "n=7"
    with pytest.warns(UserWarning, match="handler ignored"):
        assert yaml_load("{a: 1}", handlers={"merge": lambda value: 5}) == {"a": 1}


def test_expr_and_anchor():
    with pytest.warns(UserWarning, match="eval.expr=TRUE"):
        assert yaml_load("!expr 123 + 456") == "123 + 456"
    assert yaml_load("!expr 123 + 456", eval_expr=True) == 579.0
    with pytest.warns(UserWarning, match="Unknown anchor: blargh"):
        assert str(yaml_load("*blargh")) == "_yaml.bad-anchor_"


def test_named_list_keys():
    record = yaml_load("123: yes", as_named_list=False)
    assert record.keys == [123]
    assert record[0] is True


def test_read_and_write_and_load_file(tmp_path: Path):
    source = tmp_path / "in.yml"
    source.write_text("flag: y\noct: 015\n", encoding="utf-8")
    loaded = read_yaml(str(source))
    assert loaded == {"flag": True, "oct": 13}
    assert read_yaml(text="flag: n\n") == {"flag": False}
    target = tmp_path / "out.yml"
    written = write_yaml({"foo": Vector([1, 2, 3], "integer")}, str(target))
    assert target.read_text(encoding="utf-8") == written
    assert written == "foo:\n- 1\n- 2\n- 3\n"
    words = tmp_path / "words.yml"
    words.write_text("- hey\n- hi\n- hello\n", encoding="utf-8")
    assert list(yaml_load_file(str(words))) == ["hey", "hi", "hello"]


def test_verbatim_logical():
    text = as_yaml(Vector([True, False], "logical"), handlers={"logical": verbatim_logical})
    assert text == "- true\n- false\n"


def _fail(_text):
    raise RuntimeError("no")


def test_error_label_prefixes_the_message():
    with pytest.raises(YamlError, match=r"\(demo\) Duplicate map key"):
        yaml_load("a: 1\na: 2", error_label="demo")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert yaml_load("") is None
