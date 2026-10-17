import io

from utf8 import (
    as_utf8,
    output_ansi,
    output_utf8,
    utf8_encode,
    utf8_format,
    utf8_normalize,
    utf8_print,
    utf8_valid,
    utf8_width,
)


def test_as_utf8_composes_and_decodes_bytes():
    assert as_utf8("A\u030a", normalize=True) == "\u00c5"
    assert as_utf8(b"fa\xc3\xa7ile") == "fa\u00e7ile"


def test_utf8_valid_accepts_text_and_utf8_bytes():
    assert utf8_valid("fa\u00e7ile") is True
    assert utf8_valid(b"fa\xc3\xa7ile") is True
    assert utf8_valid(b"fa\xe7ile") is False


def test_utf8_normalize_matches_the_probed_maps():
    assert utf8_normalize(["\u00c5", "A\u030a", "\u212b"]) == ["\u00c5", "\u00c5", "\u00c5"]
    assert utf8_normalize("Stra\u00dfe", map_case=True) == "strasse"
    assert utf8_normalize("\u03a3", map_case=True) == "\u03c3"
    assert utf8_normalize("\ufb01", map_compat=True) == "fi"
    assert utf8_normalize("\u00c5", map_case=True, map_compat=True) == "\u00c5"
    assert utf8_normalize("ABC", map_case=True, map_compat=True) == "abc"
    assert utf8_normalize("\u2018\u2019\u201b\u055a\uff07", map_quote=True) == "'''''"
    assert utf8_normalize("a\u00adb", remove_ignorable=True) == "ab"
    assert utf8_normalize("a\u034fb", remove_ignorable=True) == "ab"
    assert utf8_normalize("a\ufff9b", remove_ignorable=True) == "a\ufff9b"


def test_utf8_width_uses_the_utf8lite_table():
    assert utf8_width(["fa\u00e7ile", "\U0001f600", "\u4e16", "e\u0301"]) == [6, 2, 2, 1]
    assert utf8_width("a\nb", encode=False) is None
    assert utf8_width('"', quote=True) == 4
    assert utf8_width("fa\u00e7ile", utf8=False) == 11


def test_utf8_encode_escapes_controls_and_styles_the_first_backslash():
    assert utf8_encode("hello\nworld") == "hello\\nworld"
    assert utf8_encode("fa\u00e7ile", utf8=False) == "fa\\u00e7ile"
    assert utf8_encode(b"fa\xc3\xa7ile") == "fa\\xc3\\xa7ile"
    styled = utf8_encode("hello\nstyled\\world", escapes="1")
    assert styled.encode() == bytes.fromhex(
        "68656c6c6f1b5b316d5c6e1b5b306d7374796c65641b5b316d5c1b5b306d5c776f726c64"
    )


def test_utf8_format_truncates_and_pads():
    assert utf8_format("fa\u00e7ile", chars=3) == "fa\u00e7\u2026"
    assert utf8_format("fa\u00e7ile", chars=3, justify="right") == "\u2026ile"
    assert utf8_format("fa\u00e7ile", chars=3, justify="centre", width=10) == "   fa\u00e7\u2026   "
    assert utf8_format(["a", "bbb"], justify="right") == ["  a", "bbb"]


def test_utf8_print_lays_out_a_named_vector():
    buf = io.StringIO()
    returned = utf8_print({"a": "fa\u00e7ile", "b": "x"}, chars=3, file=buf)
    assert returned == {"a": "fa\u00e7ile", "b": "x"}
    assert buf.getvalue() == 'a      b     \n"fa\u00e7\u2026" "x"   \n'
    unnamed = io.StringIO()
    utf8_print(["fa\u00e7ile"], chars=3, file=unnamed)
    assert unnamed.getvalue() == '[1] "fa\u00e7\u2026"\n'


def test_output_flags_follow_the_locale_and_terminal():
    assert output_utf8() is True
    assert output_ansi() is False
