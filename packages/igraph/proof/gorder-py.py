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
    gorder,
    missing_arg,
)


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


def bare(n, directed, frm, to):
    return Graph(
        0,
        pointer=False,
        n_slot=n,
        directed=directed,
        from_=frm,
        to=to,
    )


g_ring = Graph(10)
g_empty0 = Graph(0)
g_empty1 = Graph(1)
g_empty5 = Graph(5)
g_dir = Graph(4)
g_named = Graph(7)
g_color = Graph(10)
g_deleted = Graph(7)
g_added = Graph(7)
g_full = Graph(6)
g_star = Graph(8)
g_sub = Graph(4, classes=("foo", "igraph"))
g_big = Graph(100000)
g_slot = Graph(10, n_slot=Real(99))
g_clear = bare(
    Real(6),
    Logical(False),
    Real(1, 2, 3, 4, 5, 5),
    Real(0, 1, 2, 3, 4, 0),
)
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
g_r10000 = bare(Real(10000), Logical(False), Int(), Int())
g_r99999 = bare(Real(99999), Logical(False), Int(), Int())
g_r1e5 = bare(Real(1e5), Logical(False), Int(), Int())
g_r1e6 = bare(Real(1e6), Logical(False), Int(), Int())


def one():
    parts = [
        "ring10=" + show(lambda: gorder(g_ring)),
        "empty0=" + show(lambda: gorder(g_empty0)),
        "empty1=" + show(lambda: gorder(g_empty1)),
        "empty5=" + show(lambda: gorder(g_empty5)),
        "directed=" + show(lambda: gorder(g_dir)),
        "named=" + show(lambda: gorder(g_named)),
        "color=" + show(lambda: gorder(g_color)),
        "deleted=" + show(lambda: gorder(g_deleted)),
        "added=" + show(lambda: gorder(g_added)),
        "full=" + show(lambda: gorder(g_full)),
        "star=" + show(lambda: gorder(g_star)),
        "subclass=" + show(lambda: gorder(g_sub)),
        "big=" + show(lambda: gorder(g_big)),
        "slot99=" + show(lambda: gorder(g_slot)),
        "named_arg=" + show(lambda: gorder(graph=g_ring)),
        "cleared=" + show(lambda: gorder(g_clear)),
        "restore5=" + show(lambda: gorder(g_r5)),
        "restore0=" + show(lambda: gorder(g_r0)),
        "frac=" + show(lambda: gorder(g_frac)),
        "neg0=" + show(lambda: gorder(g_neg0)),
        "first=" + show(lambda: gorder(g_first)),
        "neg=" + show(lambda: gorder(g_neg)),
        "na_n=" + show(lambda: gorder(g_na)),
        "nan_n=" + show(lambda: gorder(g_nan)),
        "inf_n=" + show(lambda: gorder(g_inf)),
        "ninf_n=" + show(lambda: gorder(g_ninf)),
        "huge=" + show(lambda: gorder(g_huge)),
        "int_n=" + show(lambda: gorder(g_intn)),
        "null_n=" + show(lambda: gorder(g_nulln)),
        "dir_null=" + show(lambda: gorder(g_dir_null)),
        "dir_num=" + show(lambda: gorder(g_dir_num)),
        "dir_int=" + show(lambda: gorder(g_dir_int)),
        "dir_two=" + show(lambda: gorder(g_dir_two)),
        "edges=" + show(lambda: gorder(g_edges)),
        "edges_dbl=" + show(lambda: gorder(g_edges_dbl)),
        "oor=" + show(lambda: gorder(g_oor)),
        "neg_edge=" + show(lambda: gorder(g_neg_edge)),
        "na_edge=" + show(lambda: gorder(g_na_edge)),
        "self=" + show(lambda: gorder(g_self)),
        "tolong=" + show(lambda: gorder(g_tolong)),
        "n10000=" + show(lambda: gorder(g_r10000)),
        "n99999=" + show(lambda: gorder(g_r99999)),
        "n1e5=" + show(lambda: gorder(g_r1e5)),
        "n1e6=" + show(lambda: gorder(g_r1e6)),
        "len11=" + show(lambda: gorder(g_len11)),
        "len0=" + show(lambda: gorder(g_len0)),
        "len10=" + show(lambda: gorder(g_len10)),
        "len12=" + show(lambda: gorder(g_len12)),
        "env_list=" + show(lambda: gorder(g_env_list)),
        "atom10=" + show(lambda: gorder(g_atom10)),
        "atom5=" + show(lambda: gorder(g_atom5)),
        "atom11=" + show(lambda: gorder(g_atom11)),
        "foo=" + show(lambda: gorder(g_foo)),
        "null=" + show(lambda: gorder(None)),
        "missing=" + show(lambda: gorder()),
        "missing_arg=" + show(lambda: gorder(missing_arg())),
        "numeric=" + show(lambda: gorder([0.0] * 10)),
        "number=" + show(lambda: gorder(1)),
        "list=" + show(lambda: gorder([])),
        "data_frame=" + show(lambda: gorder({"a": 1})),
        "na=" + show(lambda: gorder(float("nan"))),
        "character=" + show(lambda: gorder("igraph")),
        "edges_frac=" + show(lambda: gorder(g_edges_frac)),
        "edges_tofrac=" + show(lambda: gorder(g_edges_tofrac)),
    ]
    return "|".join(parts)


out = Path("/home/ahmed/killr_projects/killr/packages/igraph/docs/output/gorder-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
ring = gorder(Graph(10))
example = "[1] " + r_deparse(ring) + "\n[1] " + r_deparse(gorder(Graph(10))) + "\n"
out.write_text(example, encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", "\\n")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
