import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from igraph.is_named import Graph, IgraphError, LegacyGraph, is_named


def show(fn):
    try:
        val = fn()
    except IgraphError as exc:
        return "ERR " + str(exc)
    if val is True:
        return "TRUE"
    if val is False:
        return "FALSE"
    return "VAL " + repr(val)


g_ring = Graph()
g_named = Graph(["name"])
g_color = Graph(["color"])
g_edge = Graph()
g_Name = Graph(["Name"])
g_names = Graph(["names"])
g_na = Graph(["name"])
g_num = Graph(["name"])
g_deleted = Graph()
g_empty = Graph()
g_empty_named = Graph(["name"])
g_color_name = Graph(["color", "name"])
g_name_color = Graph(["name", "color"])
g_space = Graph(["name "])
g_lead = Graph([" name"])
g_blank = Graph([""])
g_dir = Graph()
g_dir_named = Graph(["name"])
g_sub = Graph(classes=("foo", "igraph"))
g_sub_named = Graph(["name"], classes=("foo", "igraph"))
g_len11 = LegacyGraph(11)
g_len0 = LegacyGraph(0)
g_len10 = LegacyGraph(10)


def one():
    parts = [
        "ring=" + show(lambda: is_named(g_ring)),
        "named=" + show(lambda: is_named(g_named)),
        "color=" + show(lambda: is_named(g_color)),
        "edge_name=" + show(lambda: is_named(g_edge)),
        "Name=" + show(lambda: is_named(g_Name)),
        "names=" + show(lambda: is_named(g_names)),
        "na_name=" + show(lambda: is_named(g_na)),
        "num_name=" + show(lambda: is_named(g_num)),
        "deleted=" + show(lambda: is_named(g_deleted)),
        "empty=" + show(lambda: is_named(g_empty)),
        "empty_named=" + show(lambda: is_named(g_empty_named)),
        "color_name=" + show(lambda: is_named(g_color_name)),
        "name_color=" + show(lambda: is_named(g_name_color)),
        "space=" + show(lambda: is_named(g_space)),
        "lead_space=" + show(lambda: is_named(g_lead)),
        "blank=" + show(lambda: is_named(g_blank)),
        "directed=" + show(lambda: is_named(g_dir)),
        "directed_named=" + show(lambda: is_named(g_dir_named)),
        "subclass=" + show(lambda: is_named(g_sub)),
        "subclass_named=" + show(lambda: is_named(g_sub_named)),
        "len11=" + show(lambda: is_named(g_len11)),
        "len0=" + show(lambda: is_named(g_len0)),
        "len10=" + show(lambda: is_named(g_len10)),
        "null=" + show(lambda: is_named(None)),
        "missing=" + show(lambda: is_named()),
        "numeric=" + show(lambda: is_named([0.0] * 10)),
        "list=" + show(lambda: is_named([])),
        "data_frame=" + show(lambda: is_named({"a": 1})),
        "na=" + show(lambda: is_named(float("nan"))),
        "character=" + show(lambda: is_named("igraph")),
    ]
    return "|".join(parts)


out = Path("/home/ahmed/killr_projects/killr/packages/igraph/docs/output/is_named-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
example = "\n".join(
    [
        "[1] FALSE" if not is_named(Graph()) else "[1] TRUE",
        "[1] TRUE" if is_named(Graph(["name"])) else "[1] FALSE",
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
