import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from igraph.is_directed import (
    NA,
    Character,
    Complex,
    Graph,
    IgraphError,
    Int,
    ListVec,
    Logical,
    Real,
    is_directed,
    missing_arg,
)


def show(fn):
    try:
        val = fn()
    except IgraphError as exc:
        return "ERR " + str(exc)
    if val is True:
        text = "TRUE"
    elif val is False:
        text = "FALSE"
    elif val is NA:
        text = "NA"
    else:
        text = repr(val)
    return (
        "VAL "
        + text
        + " TYPE logical LEN 1 NAMES NULL MODE logical"
    )


def bare(n, directed, frm=None, to=None):
    if frm is None:
        frm = Int()
    if to is None:
        to = Int()
    return Graph(
        pointer=False,
        n_slot=n,
        directed_slot=directed,
        from_=frm,
        to=to,
    )


def cache_bit():
    graph = bare(Real(4), Logical(True))
    first = is_directed(graph)
    graph.directed = Logical(False)
    second = is_directed(graph)
    slot = graph.directed.values[0]

    def word(value):
        if value is True:
            return "TRUE"
        if value is False:
            return "FALSE"
        if value is NA:
            return "NA"
        return repr(value)

    return (
        "first="
        + word(first)
        + ",second="
        + word(second)
        + ",slot="
        + word(slot)
    )


ring4_from = Int(0, 1, 2, 3)
ring4_to = Int(1, 2, 3, 0)

g_ring = Graph(10, False)
g_dir = Graph(10, True)
g_empty = Graph(0, True)
g_empty_f = Graph(0, False)
g_full = Graph(4, True)
g_star = Graph(5, True)
g_star_u = Graph(5, False)
g_named = Graph(4, True)
g_sub = Graph(3, True, classes=("foo", "igraph"))
g_slot_u = Graph(6, False, directed_slot=Logical(True))
g_slot_d = Graph(6, True, directed_slot=Logical(False))
g_clear_u = Graph(4, False, pointer=False, from_=ring4_from, to=ring4_to)
g_clear_d = Graph(4, True, pointer=False, from_=ring4_from, to=ring4_to)
g_clear_flip = Graph(4, True, pointer=False, from_=ring4_from, to=ring4_to)
g_len11 = Graph(length=11, env=False)
g_len0 = Graph(length=0, env=False)
g_len10 = Graph(length=10, env=False)
g_len12 = Graph(length=12, env=False)
g_env_list = Graph(length=10, env=[])
g_atom10 = Graph(length=10, atomic="integer", env=False)
g_atom11 = Graph(length=11, atomic="integer", env=False)
g_atom5 = Graph(length=5, atomic="integer", env=False)
g_foo = Graph(classes=("foo",), length=0, env=False)
g_bare_f = bare(Real(3), Logical(False))
g_bare_t = bare(Real(3), Logical(True))
g_bare_na = bare(Real(3), Logical(NA))
g_bare_two = bare(Real(4), Logical(True, False))
g_bare_twof = bare(Real(4), Logical(False, True))
g_bare_natrue = bare(Real(2), Logical(NA, True))
g_na_edges = bare(Real(3), Logical(NA), Int(0, 1), Int(1, 0))
g_n_first = bare(Real(5, 1), Logical(False, True))
g_neg0 = bare(Real(-0.0), Logical(True))
g_frac = bare(Real(2.9), Logical(False))
g_edges = bare(Real(3), Logical(True), Int(0, 1), Int(1, 2))
g_edges_u = bare(Real(3), Logical(False), Int(0, 1), Int(1, 2))
g_dbl = bare(Real(3), Logical(True), Real(0, 1), Real(1, 2))
g_self = bare(Real(1), Logical(True), Int(0), Int(0))
g_tolong = bare(Real(3), Logical(True), Int(0, 1), Int(1, 2, 0))
g_dir_null = bare(Real(3), None)
g_dir_num = bare(Real(3), Real(1))
g_dir_int = bare(Real(3), Int(1))
g_dir_char = bare(Real(2), Character("TRUE"))
g_dir_list = bare(Real(2), ListVec(True))
g_dir_cplx = bare(Real(2), Complex(1 + 0j))
g_int_n = bare(Int(4), Character("x"))
g_null_n = bare(None, Logical(True))
g_char_n = bare(Character("3"), Logical(True))
g_log_n = bare(Logical(True), Logical(True))
g_na_char = bare(Real(float("nan")), Character("x"))
g_neg_null = bare(Real(-1), None)
g_neg = bare(Real(-1), Logical(True))
g_na_n = bare(Real(float("nan")), Logical(True))
g_nan_n = bare(Real(float("nan")), Logical(False))
g_inf_n = bare(Real(float("inf")), Logical(True))
g_ninf = bare(Real(float("-inf")), Logical(True))
g_huge = bare(Real(1e20), Logical(False))
g_oor = bare(Real(2), Logical(True), Int(0, 1), Int(1, 2))
g_neg_edge = bare(Real(3), Logical(True), Int(-1, 0), Int(0, 1))
g_na_edge = bare(Real(3), Logical(False), Int(-2147483648, 0), Int(1, 2))
g_frac_e = bare(Real(3), Logical(True), Real(0.5, 1), Real(1, 2))
g_tofrac = bare(Real(3), Logical(False), Int(0, 1), Real(1, 0.5))


def one():
    parts = [
        "ring=" + show(lambda: is_directed(g_ring)),
        "directed=" + show(lambda: is_directed(g_dir)),
        "empty=" + show(lambda: is_directed(g_empty)),
        "empty_f=" + show(lambda: is_directed(g_empty_f)),
        "full=" + show(lambda: is_directed(g_full)),
        "star_out=" + show(lambda: is_directed(g_star)),
        "star_u=" + show(lambda: is_directed(g_star_u)),
        "named=" + show(lambda: is_directed(g_named)),
        "subclass=" + show(lambda: is_directed(g_sub)),
        "slot_u=" + show(lambda: is_directed(g_slot_u)),
        "slot_d=" + show(lambda: is_directed(g_slot_d)),
        "named_arg=" + show(lambda: is_directed(g_dir)),
        "clear_u=" + show(lambda: is_directed(g_clear_u)),
        "clear_d=" + show(lambda: is_directed(g_clear_d)),
        "clear_flip=" + show(lambda: is_directed(g_clear_flip)),
        "cache=" + cache_bit(),
        "bare_f=" + show(lambda: is_directed(g_bare_f)),
        "bare_t=" + show(lambda: is_directed(g_bare_t)),
        "bare_na=" + show(lambda: is_directed(g_bare_na)),
        "bare_two=" + show(lambda: is_directed(g_bare_two)),
        "bare_twof=" + show(lambda: is_directed(g_bare_twof)),
        "bare_natrue=" + show(lambda: is_directed(g_bare_natrue)),
        "na_edges=" + show(lambda: is_directed(g_na_edges)),
        "n_first=" + show(lambda: is_directed(g_n_first)),
        "neg0=" + show(lambda: is_directed(g_neg0)),
        "frac=" + show(lambda: is_directed(g_frac)),
        "edges=" + show(lambda: is_directed(g_edges)),
        "edges_u=" + show(lambda: is_directed(g_edges_u)),
        "dbl_edges=" + show(lambda: is_directed(g_dbl)),
        "self=" + show(lambda: is_directed(g_self)),
        "tolong=" + show(lambda: is_directed(g_tolong)),
        "len11=" + show(lambda: is_directed(g_len11)),
        "len0=" + show(lambda: is_directed(g_len0)),
        "len10=" + show(lambda: is_directed(g_len10)),
        "len12=" + show(lambda: is_directed(g_len12)),
        "env_list=" + show(lambda: is_directed(g_env_list)),
        "atom10=" + show(lambda: is_directed(g_atom10)),
        "atom11=" + show(lambda: is_directed(g_atom11)),
        "atom5=" + show(lambda: is_directed(g_atom5)),
        "foo=" + show(lambda: is_directed(g_foo)),
        "null=" + show(lambda: is_directed(None)),
        "missing=" + show(lambda: is_directed()),
        "missarg=" + show(lambda: is_directed(missing_arg())),
        "numeric=" + show(lambda: is_directed([0.0] * 10)),
        "number=" + show(lambda: is_directed(1)),
        "list=" + show(lambda: is_directed([])),
        "data_frame=" + show(lambda: is_directed({"a": 1})),
        "na=" + show(lambda: is_directed(float("nan"))),
        "character=" + show(lambda: is_directed("igraph")),
        "dir_null=" + show(lambda: is_directed(g_dir_null)),
        "dir_num=" + show(lambda: is_directed(g_dir_num)),
        "dir_int=" + show(lambda: is_directed(g_dir_int)),
        "dir_char=" + show(lambda: is_directed(g_dir_char)),
        "dir_list=" + show(lambda: is_directed(g_dir_list)),
        "dir_cplx=" + show(lambda: is_directed(g_dir_cplx)),
        "int_n=" + show(lambda: is_directed(g_int_n)),
        "null_n=" + show(lambda: is_directed(g_null_n)),
        "char_n=" + show(lambda: is_directed(g_char_n)),
        "log_n=" + show(lambda: is_directed(g_log_n)),
        "na_char=" + show(lambda: is_directed(g_na_char)),
        "neg_null=" + show(lambda: is_directed(g_neg_null)),
        "neg=" + show(lambda: is_directed(g_neg)),
        "na_n=" + show(lambda: is_directed(g_na_n)),
        "nan_n=" + show(lambda: is_directed(g_nan_n)),
        "inf_n=" + show(lambda: is_directed(g_inf_n)),
        "ninf=" + show(lambda: is_directed(g_ninf)),
        "huge=" + show(lambda: is_directed(g_huge)),
        "oor=" + show(lambda: is_directed(g_oor)),
        "neg_edge=" + show(lambda: is_directed(g_neg_edge)),
        "na_edge=" + show(lambda: is_directed(g_na_edge)),
        "edges_frac=" + show(lambda: is_directed(g_frac_e)),
        "tofrac=" + show(lambda: is_directed(g_tofrac)),
    ]
    return "|".join(parts)


out = Path("/home/ahmed/killr_projects/killr/packages/igraph/docs/output/is_directed-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)


def printed(value):
    if value is True:
        return "[1] TRUE"
    if value is False:
        return "[1] FALSE"
    return "[1] NA"


example = "\n".join(
    [
        printed(is_directed(Graph(10, False))),
        printed(is_directed(Graph(10, True))),
    ]
)
out.write_text(example + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", "\\n")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
