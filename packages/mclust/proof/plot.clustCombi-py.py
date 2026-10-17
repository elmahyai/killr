import matplotlib

matplotlib.use("Agg")

import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))
sys.path.insert(0, str(PROOF))

from matplotlib.figure import Figure  # noqa: E402

from mclust.clust_combi import _comb_mat, clust_combi  # noqa: E402
from mclust.plot_clust_combi import (  # noqa: E402
    _classes_of,
    _combi_tree_data,
    _merge_order,
    combi_plot,
    ent_plot,
    entropy_path,
    pcws2_reg,
    plot_clust_combi,
)
from plot_trace import compare_logs, format_log, read_r_log  # noqa: E402

DOCS = PROOF.parent / "docs" / "output"


def load(stem: str) -> np.ndarray:
    return np.loadtxt(PROOF / f"{stem}.csv", ndmin=2)


def load_all() -> dict[str, np.ndarray]:
    return {
        "X6": load("clustCombi_data"),
        "Z6": load("clustCombi_z"),
        "X1": load("plot.clustCombi_d1_data"),
        "Z1": load("plot.clustCombi_d1_z"),
        "X3": load("plot.clustCombi_d3_data"),
        "Z3": load("plot.clustCombi_d3_z"),
        "X2": load("plot.clustCombi_d2g2_data"),
        "Z2": load("plot.clustCombi_d2g2_z"),
    }


D = load_all()


def make(X: np.ndarray, Z: np.ndarray, G: int):
    return clust_combi(object={"data": X, "z": Z, "G": G})


cc = {
    "G6_p2": make(D["X6"], D["Z6"], 6),
    "G4_p1": make(D["X1"], D["Z1"], 4),
    "G4_p3": make(D["X3"], D["Z3"], 4),
    "G2_p2": make(D["X2"], D["Z2"], 2),
}


def read_cases(name: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in read_r_log(PROOF / name):
        if line.startswith("#CASE\t"):
            current = line.split("\t", 1)[1]
            out[current] = []
        else:
            out[current].append(line)
    return out


overall = True
worst = 0.0


def report(label: str, r_lines: list[str], canvas) -> None:
    global overall, worst
    res = compare_logs(r_lines, format_log(canvas.log))
    overall = overall and res["matches"]
    worst = max(worst, res["max_abs_diff"])
    print(f"{label}: matches {'yes' if res['matches'] else 'no'} entries {res['n_py']} "
          f"max_abs_diff {res['max_abs_diff']:.3g}"
          + ("" if res["matches"] else f" first_mismatch {res['first_mismatch']}"))


# ---- plot.clustCombi -------------------------------------------------------
pc_r = read_cases("plot.clustCombi-r-log.txt")
for name, obj in cc.items():
    canvas = plot_clust_combi(obj)
    report(f"plot.clustCombi case {name} (G {obj['MclustOutput']['G']})", pc_r[name], canvas)

# ---- entPlot -----------------------------------------------------------------
ent_r = read_cases("entPlot-r-log.txt")
canvas = ent_plot(D["Z6"], cc["G6_p2"]["combiM"])
report("entPlot case G6_default", ent_r["G6_default"], canvas)
canvas = ent_plot(D["Z6"], cc["G6_p2"]["combiM"], reg=(3,))
report("entPlot case G6_reg3", ent_r["G6_reg3"], canvas)

# ---- combiPlot ---------------------------------------------------------------
cp_r = read_cases("combiPlot-r-log.txt")
canvas = combi_plot(D["X6"], D["Z6"], _comb_mat(6, 2, 4))
report("combiPlot case G6_p2_merge24", cp_r["G6_p2_merge24"], canvas)
canvas = combi_plot(D["X3"], D["Z3"], np.eye(4))
report("combiPlot case G4_p3_identity", cp_r["G4_p3_identity"], canvas)
canvas = combi_plot(D["X1"], D["Z1"], _comb_mat(4, 1, 3))
report("combiPlot case G4_p1_merge13", cp_r["G4_p1_merge13"], canvas)

print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")


# ---- figures for the docs (each a separate page) -------------------------------
def save(fig: Figure, name: str) -> None:
    fig.savefig(DOCS / name)


obj = cc["G6_p2"]
f = Figure(figsize=(7, 4)); plot_clust_combi(obj, what=("classification",), fig=f); save(f, "plot.clustCombi-G6_p2-classification-python.svg")
f = Figure(figsize=(8, 4)); plot_clust_combi(obj, what=("entropy",), fig=f); save(f, "plot.clustCombi-G6_p2-entropy-python.svg")
f = Figure(figsize=(6, 5)); plot_clust_combi(obj, what=("tree",), fig=f); save(f, "plot.clustCombi-G6_p2-tree-python.svg")
f = Figure(figsize=(7, 7)); plot_clust_combi(cc["G4_p3"], what=("classification",), fig=f); save(f, "plot.clustCombi-G4_p3-classification-python.svg")
f = Figure(figsize=(6, 4)); combi_plot(D["X6"], D["Z6"], _comb_mat(6, 2, 4), fig=f); save(f, "combiPlot-G6_p2_merge24-python.svg")
f = Figure(figsize=(8, 4)); ent_plot(D["Z6"], obj["combiM"], fig=f); save(f, "entPlot-G6_default-python.svg")


# ---- timing: the data computation only (no drawing) ------------------------------
def clust_combi_plot_data(obj_: dict) -> None:
    """The data steps of plot.clustCombi: classification sequence, entropy, merges, tree."""
    out = obj_["MclustOutput"]
    G = int(out["G"])
    z = np.asarray(out["z"], dtype=float)
    combi_m = obj_["combiM"]
    j, i = _merge_order(combi_m, G)
    permut_z = z[:, [int(v) - 1 for v in j]]
    cm = np.eye(G)
    for K in range(G, 0, -1):
        _classes_of(permut_z, cm)
        hits = np.flatnonzero(np.asarray(j) == i[K - 1]) + 1
        l1 = int(hits[0]) if hits.size else 0
        cm = _comb_mat(K, l1, K) @ cm
    ent, mergedn = entropy_path(z, combi_m)
    xs = np.arange(1, G + 1, dtype=float)
    pcws2_reg(xs, ent)
    pcws2_reg(np.concatenate([[0.0], np.cumsum(mergedn)]), ent)
    _combi_tree_data(obj_, "entropy")


def one() -> None:
    clust_combi_plot_data(cc["G6_p2"])


def time_median(fn) -> float:
    fn()
    timed = []
    for _ in range(20):
        started = time.perf_counter()
        fn()
        timed.append((time.perf_counter() - started) * 1000)
    return statistics.median(timed)


r_ms = float((PROOF / "plot.clustCombi-r-ms.txt").read_text())
t_ms = time_median(one)
print(f"plot.clustCombi r_ms {r_ms:.17g} translated_ms {t_ms:.17g} speedup {r_ms / t_ms:.17g}")

r_ms = float((PROOF / "entPlot-r-ms.txt").read_text())
def ent_data() -> None:
    combi_m = cc["G6_p2"]["combiM"]
    ent, mergedn = entropy_path(D["Z6"], combi_m)
    pcws2_reg(np.arange(1, 7.0), ent)
    pcws2_reg(np.concatenate([[0.0], np.cumsum(mergedn)]), ent)


t_ms = time_median(ent_data)
print(f"entPlot r_ms {r_ms:.17g} translated_ms {t_ms:.17g} speedup {r_ms / t_ms:.17g}")

r_ms = float((PROOF / "combiPlot-r-ms.txt").read_text())
t_ms = time_median(lambda: _classes_of(D["Z6"], _comb_mat(6, 2, 4)))
print(f"combiPlot r_ms {r_ms:.17g} translated_ms {t_ms:.17g} speedup {r_ms / t_ms:.17g}")
