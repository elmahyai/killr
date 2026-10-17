"""Small utils exports against R 4.5.0."""

import io

from utils.small import (
    URLdecode,
    URLencode,
    alarm,
    combn,
    compareVersion,
    glob2rx,
    hasName,
    modifyList,
)


def test_glob_examples():
    assert glob2rx("abc.*") == r"^abc\."
    assert glob2rx("a?b.*") == r"^a.b\."
    assert glob2rx("a?b.*", trim_tail=False) == r"^a.b\..*$"
    assert glob2rx("*.doc") == r"^.*\.doc$"
    assert glob2rx("*.doc", trim_head=True) == r"\.doc$"
    assert glob2rx("*.t*") == r"^.*\.t"
    assert glob2rx("*.t??") == r"^.*\.t..$"
    assert glob2rx("*[*") == r"^.*\["


def test_compare_version_and_names():
    assert compareVersion("1.0", "1.0-1") == -1
    assert compareVersion("2", "1.9.9") == 1
    assert compareVersion("1.2", "1.2") == 0
    assert hasName({"a": 1, "b": 2}, ["b", "c", "a"]) == [True, False, True]


def test_combn_column_order():
    assert combn(4, 2) == [[1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4]]


def test_url_and_modify_list():
    assert URLencode("a b") == "a%20b"
    assert URLencode("a%20b") == "a%20b"
    assert URLencode("a/b", reserved=True) == "a%2Fb"
    assert URLencode("héllo") == "h%C3%A9llo"
    assert URLdecode("%C3%A9") == "é"
    assert modifyList({"a": 1, "b": {"x": 1}}, {"b": {"y": 2}, "a": None}) == {
        "b": {"x": 1, "y": 2}
    }


def test_alarm_writes_the_bell():
    buf = io.StringIO()
    alarm(buf)
    assert buf.getvalue() == "\a"
