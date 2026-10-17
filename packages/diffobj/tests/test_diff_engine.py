"""Formatted diffs against as.character() from diffobj 0.3.9, width 80, raw, pager off."""

from diffobj.capt import Call
from diffobj.diff import (
    DiffError,
    diffChr,
    diffCsv,
    diffDeparse,
    diffFile,
    diffObj,
    diffPrint,
    diffStr,
)

_RAW = dict(format="raw", pager="off")

# diffChr(letters[1:6], c("b","CC","DD","d","f"), tar.banner="a", cur.banner="b")
_CHR = [
    "< a          > b        ",
    "@@ 1,6 @@    @@ 1,5 @@  ",
    "< a          ~          ",
    "  b            b        ",
    "< c          > CC       ",
    "~            > DD       ",
    "  d            d        ",
    "< e          ~          ",
    "  f            f        ",
]
_SAME = [
    "No visible differences between objects.",
    "< a          > b        ",
    "@@ 1,2 @@    @@ 1,2 @@  ",
    "  a            a        ",
    "  b            b        ",
]
_PRINT = [
    '< letters                               > letters[-5]                         ',
    "@@ 1,3 @@                               @@ 1,3 @@                             ",
    '<  [1] "a" "b" "c" "d" "e" "f" "g" "h"  >  [1] "a" "b" "c" "d" "f" "g" "h" "i"',
    '   [9] "i" "j" "k" "l" "m" "n" "o" "p"     [9] "j" "k" "l" "m" "n" "o" "p" "q"',
    '  [17] "q" "r" "s" "t" "u" "v" "w" "x"    [17] "r" "s" "t" "u" "v" "w" "x" "y"',
]
_UNIFIED = [
    "< letters[1:6]   ",
    '> c("b", "CC", ..',
    "@@ 1,6 / 1,5 @@  ",
    "< a              ",
    "  b              ",
    "< c              ",
    "> CC             ",
    "> DD             ",
    "  d              ",
    "< e              ",
    "  f              ",
]
_CONTEXT = [
    "< a              ",
    "> b              ",
    "@@ 1,6 / 1,5 @@  ",
    "< a              ",
    "  b              ",
    "< c              ",
    "  d              ",
    "< e              ",
    "  f              ",
    "~ ----------",
    "  b              ",
    "> CC             ",
    "> DD             ",
    "  d              ",
    "  f              ",
]
_STR = [
    "< t              > c            ",
    "@@ 1,3 @@        @@ 1,3 @@      ",
    "  List of 2        List of 2    ",
    "   $ a: num 1       $ a: num 1  ",
    '<  $ b: chr "x"  >  $ b: chr "y"',
]
_DEPARSE = [
    "< t          > c        ",
    "@@ 1 @@      @@ 1 @@    ",
    "< foo(1, 2)  > foo(1, 3)",
]
_FILE = [
    "< t          > c        ",
    "@@ 1,3 @@    @@ 1,3 @@  ",
    "  a            a        ",
    "< b          > B        ",
    "  c            c        ",
]
_CSV = [
    "< t          > c        ",
    "@@ 1,3 @@    @@ 1,3 @@  ",
    "    a b          a b    ",
    "  1 1 x        1 1 x    ",
    "< 2 2 y      > 2 2 z    ",
]
_OBJ = [
    "< t            > c          ",
    "@@ 1 @@        @@ 1 @@      ",
    '< [1] "a" "b"  > [1] "a" "c"',
]


def _letters():
    return list("abcdefghijklmnopqrstuvwxyz")


def test_diffchr_side_by_side():
    diff = diffChr(
        list("abcdef"),
        ["b", "CC", "DD", "d", "f"],
        tar_banner="a",
        cur_banner="b",
        **_RAW,
    )
    assert diff.lines == _CHR
    assert str(diff) == "\n".join(_CHR)
    assert "\x1b" not in str(diff)


def test_diffchr_no_visible_difference():
    diff = diffChr(["a", "b"], ["a", "b"], tar_banner="a", cur_banner="b", **_RAW)
    assert diff.lines == _SAME


def test_diffchr_unified_and_context():
    target = list("abcdef")
    current = ["b", "CC", "DD", "d", "f"]
    unified = diffChr(
        target,
        current,
        mode="unified",
        tar_banner="letters[1:6]",
        cur_banner='c("b", "CC", "DD", "d", "f")',
        **_RAW,
    )
    context = diffChr(target, current, mode="context", tar_banner="a", cur_banner="b", **_RAW)
    assert unified.lines == _UNIFIED
    assert context.lines == _CONTEXT


def test_diffprint_letters():
    diff = diffPrint(
        _letters(),
        [item for item in _letters() if item != "e"],
        tar_banner="letters",
        cur_banner="letters[-5]",
        **_RAW,
    )
    assert diff.lines == _PRINT


def test_diffstr_named_list():
    diff = diffStr(
        {"a": 1, "b": "x"},
        {"a": 1, "b": "y"},
        tar_banner="t",
        cur_banner="c",
        **_RAW,
    )
    assert diff.lines == _STR


def test_diffdeparse_call():
    diff = diffDeparse(
        Call("foo", 1, 2),
        Call("foo", 1, 3),
        tar_banner="t",
        cur_banner="c",
        **_RAW,
    )
    assert diff.lines == _DEPARSE


def test_difffile(tmp_path):
    target = tmp_path / "target.txt"
    current = tmp_path / "current.txt"
    target.write_text("a\nb\nc\n")
    current.write_text("a\nB\nc\n")
    diff = diffFile(target, current, tar_banner="t", cur_banner="c", **_RAW)
    assert diff.lines == _FILE


def test_diffcsv(tmp_path):
    target = tmp_path / "target.csv"
    current = tmp_path / "current.csv"
    target.write_text("a,b\n1,x\n2,y\n")
    current.write_text("a,b\n1,x\n2,z\n")
    diff = diffCsv(str(target), str(current), tar_banner="t", cur_banner="c", **_RAW)
    assert diff.lines == _CSV


def test_diffobj_character_uses_print():
    diff = diffObj(["a", "b"], ["a", "c"], tar_banner="t", cur_banner="c", **_RAW)
    assert diff.lines == _OBJ


def test_dotted_banner_alias_and_width_zero():
    dotted = diffChr(
        list("abcdef"),
        ["b", "CC", "DD", "d", "f"],
        **{"tar.banner": "a", "cur.banner": "b", "disp.width": 0, **_RAW},
    )
    assert dotted.lines == _CHR


def test_bad_mode_pager_and_missing():
    try:
        diffChr(["a"], ["a"], mode="nope")
    except DiffError as exc:
        assert str(exc) == (
            "Argument `mode` must be character(1L) and in "
            '`c("auto", "unified", "context", "sidebyside")`.'
        )
    else:
        raise AssertionError("bad mode was accepted")
    try:
        diffChr(["a"], ["a"], pager="nope")
    except DiffError as exc:
        assert str(exc) == (
            'Argument `pager` must be one of `c("auto", "off", "on")`, '
            "a `Pager` object, or a list."
        )
    else:
        raise AssertionError("bad pager was accepted")
    try:
        diffChr(["a"])
    except DiffError as exc:
        assert str(exc) == 'argument "current" is missing, with no default'
    else:
        raise AssertionError("missing argument was accepted")
