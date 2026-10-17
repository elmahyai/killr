"""Printers, glimpse, and the defunct colonnade helpers."""

from lifecycle import LifecycleError

from pillar._vec import NULL, DataFrame, Factor, List
from pillar.colonnade import colonnade, extra_cols, squeeze
from pillar.column import (
    ctl_new_pillar,
    ctl_new_pillar_list,
    ctl_new_rowid_pillar,
    new_pillar,
    pillar,
)
from pillar.deprecated import expect_known_display, is_vector_s3
from pillar.format_tbl import (
    tbl_format_body,
    tbl_format_footer,
    tbl_format_header,
    tbl_format_setup,
    tbl_nrow,
)
from pillar.glimpse import format_glimpse, glimpse
from pillar.shaft import new_pillar_shaft, new_pillar_shaft_simple, pillar_shaft
from pillar._layout import lines_of


def _frame():
    return DataFrame({"a": [1, 2, 3], "b": ["x", "yy", "zzz"], "c": [True, False, None]})


def _join(lines):
    return "\n".join(lines)


def test_pillar_and_shafts():
    rows = pillar([1.5, None, 1000.0, -0.25, 1e10, float("-inf"), float("nan")], "x").format()
    assert _join(rows) == (
        "         x\n"
        "     <dbl>\n"
        "   1.5e+ 0\n"
        "  NA      \n"
        "   1  e+ 3\n"
        "  -2.5e- 1\n"
        "   1  e+10\n"
        "-Inf      \n"
        " NaN      "
    )
    assert lines_of(pillar_shaft([1, 2, 3]).format(width=1)) == ["1", "2", "3"]
    shaft = new_pillar_shaft(["a", "b"], width=5, min_width=3, class_="pillar_shaft_demo")
    assert (shaft.classes[0], shaft.width, shaft.min_width, shaft.data) == (
        "pillar_shaft_demo",
        5,
        3,
        ["a", "b"],
    )
    simple = new_pillar_shaft_simple(["ab", None, "cdef"], width=6, align="left")
    assert lines_of(simple.format(width=4)) == ["ab", "NA", "cdef"]
    assert _join(new_pillar(pillar([1, 2, 3], "n")).format()) == "    n\n<int>\n    1\n    2\n    3"


def test_table_pieces():
    frame = _frame()
    assert tbl_nrow(frame) == 3
    setup = tbl_format_setup(frame, width=30, n=2)
    assert _join(tbl_format_header(frame, setup)) == "# A data frame: 3 × 3"
    assert _join(tbl_format_body(frame, setup)) == (
        "      a b     c    \n"
        "* <int> <chr> <lgl>\n"
        "1     1 x     TRUE \n"
        "2     2 yy    FALSE"
    )
    assert _join(tbl_format_footer(frame, setup)) == "# ℹ 1 more row"
    shown = _join(setup.format())
    assert shown.startswith("<pillar_tbl_format_setup>\n<tbl_format_header(setup)>")
    assert shown.endswith("<tbl_format_footer(setup)>\n# ℹ 1 more row")
    assert _join(ctl_new_pillar(frame, [1, 2, 3], 60, title="n").format()) == "    n\n<int>\n    1\n    2\n    3"
    head = DataFrame({name: values[:2] for name, values in frame.columns.items()})
    pillars = ctl_new_pillar_list(frame, head, width=30)
    assert _join(pillars[0].format()).split("\n")[0] == "    a"
    assert _join(ctl_new_rowid_pillar(frame, frame, 30, type="*").format()) == " \n*\n1\n2\n3"


def test_glimpse_and_defunct():
    items = List([[1, 2, 3], "A, B", Factor(["A", "B, C"]), [], NULL])
    assert _join(format_glimpse(items)) == '<1, 2, 3>\n"A, B"\n<"A", "B, C">\n<>\n<NULL>'
    import io
    import sys

    buffer = io.StringIO()
    old = sys.stdout
    sys.stdout = buffer
    try:
        glimpse(_frame(), width=40)
    finally:
        sys.stdout = old
    text = buffer.getvalue().removesuffix("\n")
    assert text == 'Rows: 3\nColumns: 3\n$ a <int> 1, 2, 3\n$ b <chr> "x", "yy", "zzz"\n$ c <lgl> TRUE, FALSE, NA'
    for func, snippet in (
        (is_vector_s3, "is_vector_s3()"),
        (expect_known_display, "expect_known_display()"),
        (colonnade, "colonnade()"),
        (squeeze, "squeeze()"),
        (extra_cols, "extra_cols()"),
    ):
        try:
            func()
        except LifecycleError as exc:
            assert snippet in str(exc)
        else:
            raise AssertionError(snippet)
