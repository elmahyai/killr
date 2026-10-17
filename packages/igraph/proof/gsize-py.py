import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from igraph.gorder import (
    Graph,
    IgraphError,
    Int,
    Logical,
    Real,
    missing_arg,
)
from igraph.gsize import LazyEnds, gsize


def r_deparse(value: float) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1e5 and value == math.trunc(value):
        digits = str(int(magnitude))
        exponent = len(digits) - 1
        mantissa = magnitude / 10**exponent
        body = format(mantissa, ".15g")
        sign = "-" if value < 0 else ""
        return f"{sign}{body}e+{exponent:02d}"
    if value == math.trunc(value) and magnitude < 1e5:
        return str(int(value))
    return format(value, ".15g")


def show(fn):
    try:
        val = fn()
    except IgraphError as exc:
        return "ERR " + str(exc)
    if isinstance(val, float) and not isinstance(val, bool):
        return (
            "VAL "
            + r_deparse(val)
            + " TYPE double LEN 1 NAMES NULL MODE double"
        )
    return "VAL " + repr(val)


def live(n, edges, **kwargs):
    graph = Graph(n, **kwargs)
    graph.env.edges = edges
    return graph


def bare(n, directed, frm, to):
    return Graph(
        0,
        pointer=False,
        n_slot=n,
        directed=directed,
        from_=frm,
        to=to,
    )


g_ring = live(10, 10)
g_empty0 = live(0, 0)
g_empty1 = live(1, 0)
g_empty5 = live(5, 0)
g_dir = live(4, 4)
g_named = live(7, 7)
g_color = live(10, 10)
g_deleted = live(7, 6)
g_added = live(7, 3)
g_full = live(6, 30)
g_full_u = live(6, 15)
g_star = live(8, 7)
g_sub = live(4, 4, classes=("foo", "igraph"))
g_big = live(100000, 0)
g_big_ring = live(100000, 100000)
g_slot = live(10, 10, n_slot=Real(99))
g_fromslot = live(10, 10, from_=Int(0, 1))
g_clear = bare(
    Real(6),
    Logical(False),
    Real(1, 2, 3, 4, 5, 5),
    Real(0, 1, 2, 3, 4, 0),
)
g_clear_dir = bare(
    Real(4),
    Logical(True),
    Real(0, 1, 2, 3),
    Real(1, 2, 3, 0),
)
g_clear_star = bare(
    Real(8),
    Logical(False),
    Real(1, 2, 3, 4, 5, 6, 7),
    Real(0, 0, 0, 0, 0, 0, 0),
)
g_clear_empty = bare(Real(5), Logical(False), LazyEnds(), LazyEnds())
g_len11 = Graph(0, length=11, env=None, pointer=False)
g_len0 = Graph(0, length=0, env=None, pointer=False)
g_len10 = Graph(0, length=10, env=None, pointer=False)
g_len12 = Graph(0, length=12, env=None, pointer=False)
g_env_list = Graph(1, length=10, env=[], pointer=False)
g_atom10 = Graph(0, length=10, atomic="integer", env=None, pointer=False)
g_atom5 = Graph(0, length=5, atomic="integer", env=None, pointer=False)
g_atom11 = Graph(0, length=11, atomic="integer", env=None, pointer=False)
g_foo = Graph(0, classes=("foo",), length=0, env=None, pointer=False)
g_r5 = bare(Real(5), Logical(False), Int(), Int())
g_r0 = bare(Real(0), Logical(False), Int(), Int())
g_frac = bare(Real(2.9), Logical(False), Int(), Int())
g_neg0 = bare(Real(-0.0), Logical(False), Int(), Int())
g_first = bare(Real(2, 9), Logical(False), Int(), Int())
g_neg = bare(Real(-1), Logical(False), Int(), Int())
g_na = bare(Real(float("nan")), Logical(False), Int(), Int())
g_nan = bare(Real(float("nan")), Logical(False), Int(), Int())
g_inf = bare(Real(float("inf")), Logical(False), Int(), Int())
g_ninf = bare(Real(float("-inf")), Logical(False), Int(), Int())
g_huge = bare(Real(1e20), Logical(False), Int(), Int())
g_intn = bare(Int(4), Logical(False), Int(), Int())
g_nulln = bare(None, Logical(False), Int(), Int())
g_dir_null = bare(Real(3), None, Int(), Int())
g_dir_num = bare(Real(3), Real(1), Int(), Int())
g_dir_int = bare(Real(3), Int(1), Int(), Int())
g_dir_two = bare(Real(4), Logical(True, False), Int(), Int())
g_edges = bare(Real(3), Logical(False), Int(0, 1), Int(1, 2))
g_edges_dbl = bare(Real(3), Logical(False), Real(0, 1), Real(1, 2))
g_edges_frac = bare(Real(3), Logical(False), Real(0.5, 1), Int(1, 2))
g_edges_tofrac = bare(Real(3), Logical(False), Int(0, 1), Real(1, 0.5))
g_oor = bare(Real(2), Logical(False), Int(0, 1), Int(1, 2))
g_neg_edge = bare(Real(3), Logical(False), Int(-1, 0), Int(0, 1))
g_na_edge = bare(Real(3), Logical(False), Int(-2147483648, 0), Int(1, 2))
g_self = bare(Real(1), Logical(False), Int(0), Int(0))
g_tolong = bare(Real(3), Logical(False), Int(0, 1), Int(1, 2, 0))
g_multi = bare(Real(4), Logical(True), Int(0, 0, 1), Int(1, 1, 2))
g_loop = bare(Real(2), Logical(False), Int(0, 1), Int(0, 1))
g_one = bare(Real(4), Logical(True), Int(0), Int(3))
g_many = bare(Real(10), Logical(False), Int(*range(9)), Int(*range(1, 10)))
g_dir_edge = bare(Real(3), Logical(True), Int(2, 0), Int(0, 1))
g_r10000 = bare(Real(10000), Logical(False), Int(), Int())
g_r1e6 = bare(Real(1e6), Logical(False), Int(), Int())
g_to_extra = bare(Real(3), Logical(False), Int(), Int(0, 1))
g_keep = bare(Real(3), Logical(False), Int(0, 1), Int(1, 2))


def one():
    keep = show(lambda: gsize(g_keep))
    g_keep.from_ = Int()
    kept = show(lambda: gsize(g_keep))
    parts = [
        "ring10=" + show(lambda: gsize(g_ring)),
        "empty0=" + show(lambda: gsize(g_empty0)),
        "empty1=" + show(lambda: gsize(g_empty1)),
        "empty5=" + show(lambda: gsize(g_empty5)),
        "directed=" + show(lambda: gsize(g_dir)),
        "named=" + show(lambda: gsize(g_named)),
        "color=" + show(lambda: gsize(g_color)),
        "deleted=" + show(lambda: gsize(g_deleted)),
        "added=" + show(lambda: gsize(g_added)),
        "full=" + show(lambda: gsize(g_full)),
        "full_u=" + show(lambda: gsize(g_full_u)),
        "star=" + show(lambda: gsize(g_star)),
        "subclass=" + show(lambda: gsize(g_sub)),
        "big=" + show(lambda: gsize(g_big)),
        "big_ring=" + show(lambda: gsize(g_big_ring)),
        "slot99=" + show(lambda: gsize(g_slot)),
        "fromslot=" + show(lambda: gsize(g_fromslot)),
        "named_arg=" + show(lambda: gsize(graph=g_ring)),
        "cleared=" + show(lambda: gsize(g_clear)),
        "cleared_dir=" + show(lambda: gsize(g_clear_dir)),
        "cleared_star=" + show(lambda: gsize(g_clear_star)),
        "cleared_empty=" + show(lambda: gsize(g_clear_empty)),
        "restore5=" + show(lambda: gsize(g_r5)),
        "restore0=" + show(lambda: gsize(g_r0)),
        "frac=" + show(lambda: gsize(g_frac)),
        "neg0=" + show(lambda: gsize(g_neg0)),
        "first=" + show(lambda: gsize(g_first)),
        "neg=" + show(lambda: gsize(g_neg)),
        "na_n=" + show(lambda: gsize(g_na)),
        "nan_n=" + show(lambda: gsize(g_nan)),
        "inf_n=" + show(lambda: gsize(g_inf)),
        "ninf_n=" + show(lambda: gsize(g_ninf)),
        "huge=" + show(lambda: gsize(g_huge)),
        "int_n=" + show(lambda: gsize(g_intn)),
        "null_n=" + show(lambda: gsize(g_nulln)),
        "dir_null=" + show(lambda: gsize(g_dir_null)),
        "dir_num=" + show(lambda: gsize(g_dir_num)),
        "dir_int=" + show(lambda: gsize(g_dir_int)),
        "dir_two=" + show(lambda: gsize(g_dir_two)),
        "edges=" + show(lambda: gsize(g_edges)),
        "edges_dbl=" + show(lambda: gsize(g_edges_dbl)),
        "oor=" + show(lambda: gsize(g_oor)),
        "neg_edge=" + show(lambda: gsize(g_neg_edge)),
        "na_edge=" + show(lambda: gsize(g_na_edge)),
        "self=" + show(lambda: gsize(g_self)),
        "tolong=" + show(lambda: gsize(g_tolong)),
        "multi=" + show(lambda: gsize(g_multi)),
        "loop=" + show(lambda: gsize(g_loop)),
        "one_edge=" + show(lambda: gsize(g_one)),
        "many=" + show(lambda: gsize(g_many)),
        "dir_edge=" + show(lambda: gsize(g_dir_edge)),
        "n10000=" + show(lambda: gsize(g_r10000)),
        "n1e6=" + show(lambda: gsize(g_r1e6)),
        "to_extra=" + show(lambda: gsize(g_to_extra)),
        "keep=" + keep,
        "kept=" + kept,
        "len11=" + show(lambda: gsize(g_len11)),
        "len0=" + show(lambda: gsize(g_len0)),
        "len10=" + show(lambda: gsize(g_len10)),
        "len12=" + show(lambda: gsize(g_len12)),
        "env_list=" + show(lambda: gsize(g_env_list)),
        "atom10=" + show(lambda: gsize(g_atom10)),
        "atom5=" + show(lambda: gsize(g_atom5)),
        "atom11=" + show(lambda: gsize(g_atom11)),
        "foo=" + show(lambda: gsize(g_foo)),
        "null=" + show(lambda: gsize(None)),
        "missing=" + show(lambda: gsize()),
        "missing_arg=" + show(lambda: gsize(missing_arg())),
        "numeric=" + show(lambda: gsize([0.0] * 10)),
        "number=" + show(lambda: gsize(1)),
        "list=" + show(lambda: gsize([])),
        "data_frame=" + show(lambda: gsize({"a": 1})),
        "na=" + show(lambda: gsize(float("nan"))),
        "character=" + show(lambda: gsize("igraph")),
        "edges_frac=" + show(lambda: gsize(g_edges_frac)),
        "edges_tofrac=" + show(lambda: gsize(g_edges_tofrac)),
        "ecount_alias=" + show(lambda: gsize(g_ring)),
    ]
    return "|".join(parts)


out = Path("/home/ahmed/killr_projects/killr/packages/igraph/docs/output/gsize-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
cycle = live(10, 10)
text = "[1] " + r_deparse(gsize(cycle)) + "\n[1] " + r_deparse(gsize(cycle)) + "\n"
out.write_text(text, encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", "\\n")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
