"""Checks that do not need R. The proof scripts are the R comparison."""

from cli import (
    ansi_collapse,
    ansi_substr,
    ansi_toupper,
    boxx,
    console_width,
    is_ansi_tty,
    rule,
    ansi_has_any,
    ansi_nchar,
    ansi_regex,
    ansi_strip,
    col_green,
    col_red,
    combine_ansi_styles,
    hash_md5,
    hash_sha256,
    hash_xxhash,
    hash_xxhash64,
    list_border_styles,
    make_ansi_style,
    no,
    pluralize,
    spark_bar,
    spark_line,
    style_bold,
    style_no_italic,
    symbol,
    truecolor,
    utf8_graphemes,
    utf8_nchar,
)
from cli._options import options
from cli.pluralize import _as_piece


def test_styles_match_the_installed_sequences():
    options(**{"cli.num_colors": 8})
    assert col_red("hi") == "\x1b[31mhi\x1b[39m"
    nested = col_green("A ", col_red(style_bold("B")), " C")
    assert nested == "\x1b[32mA \x1b[31m\x1b[1mB\x1b[22m\x1b[32m C\x1b[39m"
    assert style_no_italic("x") == "\x1b[0m\x1b[22m\x1b[24m\x1b[27m\x1b[28m\x1b[29m\x1b[39m\x1b[49mx\x1b[23m"
    assert make_ansi_style("orange", colors=256)("foobar") == "\x1b[38;5;214mfoobar\x1b[39m"
    assert combine_ansi_styles(style_bold, col_red)("Warning!") == "\x1b[1m\x1b[31mWarning!\x1b[39m\x1b[22m"
    options(**{"cli.num_colors": 1})
    assert col_red("hi") == "hi"


def test_substr_rule_and_box_keep_width():
    options(**{"cli.unicode": True, "cli.num_colors": 8})
    styled = col_red("red") + " default " + col_green("green")
    assert ansi_substr(styled, 1, 5) == "\x1b[31mred\x1b[39m d"
    assert ansi_toupper(col_red("Ab")) == "\x1b[31mAB\x1b[39m"
    assert rule(center="TITLE", width=20) == "─────── TITLE ──────"
    assert "Hello there!" in boxx("Hello there!", width=40)
    assert console_width() == 80
    assert is_ansi_tty() is False


def test_xxhash_graphemes_and_ansi_text():
    options(**{"cli.unicode": True, "cli.num_colors": 8})
    emo = "\U0001f477\U0001f3fb\u200d\u2640\ufe0f"
    assert hash_xxhash("foo") == "79aef92e83454121ab6e5f64077e7d8a"
    assert hash_xxhash64("foo") == "ab6e5f64077e7d8a"
    assert hash_xxhash(["foo", None])[1] is None
    assert utf8_nchar(emo, "chars") == 1
    assert utf8_nchar(emo, "width") == 2
    assert utf8_nchar(emo, "bytes") == 17
    assert utf8_nchar(emo, "codepoints") == 5
    assert utf8_graphemes(emo) == [emo]
    styled = col_red("red") + " default " + col_green("green")
    assert ansi_strip(styled) == "red default green"
    assert ansi_has_any("foobar") is False
    assert ansi_has_any(styled) is True
    assert ansi_nchar(styled, "width") == 17
    assert ansi_strip("A\x1b[2AB") == "AB"
    assert "\\x{001b}" in ansi_regex()


def test_spark_hash_plural_and_collapse():
    options(**{"cli.unicode": True, "cli.num_colors": 8})
    assert spark_bar([i / 5 for i in range(6)]) == "▁▂▄▅▇█"
    assert spark_line([i / 9 for i in range(10)]) == "⣀⡠⠔⠊⠉"
    assert spark_bar([0, None, 0.5, None, 1]) == "▁ ▄ █"
    assert hash_md5(["foo", None, "bar", ""]) == [
        "acbd18db4cc2f85cedef654fccc4a4d8",
        None,
        "37b51d194a7513e45b56f6524f2d51f2",
        "d41d8cd98f00b204e9800998ecf8427e",
    ]
    assert hash_sha256("foo") == "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
    assert symbol["tick"] == "✔"
    assert _as_piece(no(0)) == "no"
    nfile = 0
    assert pluralize("Found {no(nfile)} file{?s}.") == "Found no files."
    pkgs = ["pkg1", "pkg2", "pkg3"]
    assert pluralize("Will remove the {pkgs} package{?s}.") == "Will remove the pkg1, pkg2, and pkg3 packages."
    letters = list("abcdefghijklmnopqrstuvwxyz")
    assert ansi_collapse(letters, trunc=5) == "a, b, c, …, y, and z"
    assert list_border_styles()[0] == "single"
    assert truecolor == 256**3


def test_hashes_tree_diff_and_inline():
    from cli import (
        code_highlight,
        diff_chr,
        format_inline,
        hash_animal,
        hash_emoji,
        hash_obj_md5,
        tree,
    )
    from cli._options import options

    options(**{"cli.num_colors": 8, "cli.unicode": True})
    assert hash_emoji("foo", 1)["text"] == "sun behind cloud"
    assert hash_animal("foo", 0)["hash"] == "lion"
    assert hash_obj_md5("foo") == "bd40ef6d4a9413de9c1318a65cbae5d7"
    assert tree({"id": ["a", "b", "c"], "kids": [["b", "c"], [], []]}) == ["a", "├─b", "└─c"]
    script = diff_chr(["a", "b", "c"], ["a", "x", "c"])["lcs"]
    assert [row["operation"] for row in script] == ["match", "delete", "insert", "match"]
    assert "\x1b[3m" in format_inline("{.emph hi}")
    assert "\x1b[33m" in code_highlight("x <- 1")
