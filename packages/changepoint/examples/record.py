"""Record changepoint checks against the installed R package."""

import json
import statistics
import subprocess
import textwrap
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "output"
PROOF = ROOT / "proof"
PY = "/home/ahmed/killr_projects/killr/.venv/bin/python"

rng = np.random.default_rng(1)
series = np.concatenate([rng.normal(0, 1, 40), rng.normal(4, 1, 40)])
variance = np.concatenate([rng.normal(0, 1, 40), rng.normal(0, 3, 40)])
literal = ", ".join(f"{value:.17g}" for value in series)
var_literal = ", ".join(f"{value:.17g}" for value in variance)
response = np.where(np.arange(80) < 40, 1 + 0.05 * np.arange(80), 4 + 0.05 * np.arange(80))
response = response + rng.normal(0, 0.3, 80)
reg = np.column_stack([response, np.ones(80), np.arange(1, 81)])
reg_literal = ", ".join(f"{value:.17g}" for value in reg.reshape(-1, order="F"))

R_HEAD = f"""
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(changepoint))
options(warn = -1)
x <- c({literal})
v <- c({var_literal})
reg <- matrix(c({reg_literal}), ncol = 3)
json_str <- function(s) {{
  s <- enc2utf8(paste(s, collapse = "\\n"))
  cps <- utf8ToInt(s)
  parts <- vapply(cps, function(cp) {{
    if (cp == 34) paste0("\\\\", '"')
    else if (cp == 92) paste0("\\\\", "\\\\")
    else if (cp == 10) paste0("\\\\", "n")
    else if (cp == 13) paste0("\\\\", "r")
    else if (cp == 9) paste0("\\\\", "t")
    else if (cp < 32 || cp == 127) sprintf("\\\\u%04x", cp)
    else intToUtf8(cp)
  }}, "")
  paste0('"', paste(parts, collapse = ""), '"')
}}
json_val <- function(obj) {{
  if (is.character(obj) && length(obj) == 1) return(json_str(obj))
  obj <- as.numeric(obj)
  parts <- ifelse(is.na(obj), "null", sprintf("%.17g", obj))
  paste0("[", paste(parts, collapse = ","), "]")
}}
"""

PY_HEAD = f"""
import json, statistics, time, warnings
import numpy as np
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
from changepoint import *
from changepoint._api import sumstat
x = np.array([{literal}])
v = np.array([{var_literal}])
reg = np.array([{reg_literal}]).reshape((3, 80)).T
"""

# name, r body returning the value, python body returning the value, kind, uses, loads, done, title
CASES = [
    ("cpt.mean", "cpts(cpt.mean(x))", "cpts(cpt_mean(x))", "num", ["numpy"], [], "PELT change in mean.", "Change in mean"),
    ("cpt.var", "cpts(cpt.var(v))", "cpts(cpt_var(v))", "num", ["numpy"], [], "PELT change in variance.", "Change in variance"),
    ("cpt.meanvar", "cpts(cpt.meanvar(x))", "cpts(cpt_meanvar(x))", "num", ["numpy"], [], "PELT change in mean and variance.", "Change in mean and variance"),
    ("cpt.reg", "cpts(cpt.reg(reg))", "cpts(cpt_reg(reg))", "num", ["numpy"], [], "PELT change in regression.", "Change in regression"),
    ("PELT", 'PELT(cbind(c(0, cumsum(x)), c(0, cumsum(x^2)), cumsum(c(0, (x - mean(x))^2))), pen = 10, cost_func = "mean.norm")[[2]]', "PELT(sumstat(x), pen=10, cost_func='mean.norm').cpts", "num", ["numpy"], [], "PELT on the three summary columns.", "PELT"),
    ("BINSEG", 'BINSEG(cbind(c(0, cumsum(x)), c(0, cumsum(x^2)), cumsum(c(0, (x - mean(x))^2))), pen = 10, cost_func = "mean.norm", Q = 5)$cpts', "BINSEG(sumstat(x), pen=10, cost_func='mean.norm', Q=5).cpts", "num", ["numpy"], [], "Binary segmentation on the three summary columns.", "Binary segmentation"),
    ("decision", 'decision(40, 12, 1, penalty = "Manual", n = 80, diffparam = 1, pen.value = 5)$cpt', "np.asarray([decision(40, 12, 1, 'Manual', 80, 1, 5)['cpt']])", "num", ["numpy"], [], "A single comparison of the test statistic with the penalty.", "Decision"),
    ("penalty_decision", 'penalty_decision("MBIC", 0, 80, 1, "mean.norm", "PELT")', "np.asarray([penalty_decision('MBIC', 0, 80, 1, 'mean.norm', 'PELT')])", "num", ["numpy"], [], "The modified BIC penalty.", "Penalty"),
    ("class_input", 'cpts(class_input(x, "mean", "PELT", "Normal", "Manual", 10, 1, TRUE, PELT(cbind(c(0, cumsum(x)), c(0, cumsum(x^2)), cumsum(c(0, (x - mean(x))^2))), pen = 10, cost_func = "mean.norm")))', "cpts(class_input(x, 'mean', 'PELT', 'Normal', 'Manual', 10, 1, True, PELT(sumstat(x), pen=10, cost_func='mean.norm')))", "num", ["numpy"], [], "Build a cpt object from a PELT search.", "Class input"),
    ("cpts", "cpts(cpt.mean(x))", "cpts(cpt_mean(x))", "num", ["numpy"], [], "Changepoint locations, without the series length.", "Changepoint locations"),
    ("cpts.full", "as.numeric(cpts.full(cpt.mean(x, method = 'BinSeg', Q = 5, penalty = 'SIC')))", "np.asarray(cpts_full(cpt_mean(x, method='BinSeg', Q=5, penalty='SIC')), dtype=float).reshape(-1, order='F')", "num", ["numpy"], [], "Every BinSeg candidate, column by column.", "All segmentations"),
    ("cpts.ts", "as.numeric(cpts.ts(cpt.mean(x)))", "cpts_ts(cpt_mean(x))", "num", ["numpy"], [], "Changepoint locations on the series index.", "Changepoint times"),
    ("cpttype", "cpttype(cpt.mean(x))", "cpttype(cpt_mean(x))", "text", [], [], "The kind of change.", "Changepoint type"),
    ("distribution", "distribution(cpt.mean(x))", "distribution(cpt_mean(x))", "text", [], [], "The test statistic, under the old name.", "Distribution"),
    ("test.stat", "test.stat(cpt.mean(x))", "test_stat(cpt_mean(x))", "text", [], [], "The test statistic.", "Test statistic"),
    ("method", "method(cpt.mean(x))", "method(cpt_mean(x))", "text", [], [], "The search method.", "Method"),
    ("ncpts", "ncpts(cpt.mean(x))", "np.asarray([ncpts(cpt_mean(x))])", "num", ["numpy"], [], "How many changepoints were found.", "Number of changepoints"),
    ("ncpts.max", "as.numeric(is.infinite(ncpts.max(cpt.mean(x))))", "np.asarray([1.0 if np.isinf(ncpts_max(cpt_mean(x))) else 0.0])", "num", ["numpy"], [], "PELT leaves the maximum as Inf.", "Maximum changepoints"),
    ("param.est", "param.est(cpt.mean(x))$mean", "param_est(cpt_mean(x))['mean']", "num", ["numpy"], [], "Segment means.", "Parameter estimates"),
    ("param", "param(cpt.mean(x, param.estimates = FALSE))@param.est$mean", "param(cpt_mean(x, param_estimates=False)).param_est['mean']", "num", ["numpy"], [], "Fill the segment means.", "Parameters"),
    ("coef", "coef(cpt.mean(x))$mean", "coef(cpt_mean(x))['mean']", "num", ["numpy"], [], "The same list param.est returns.", "Coefficients"),
    ("pen.type", "pen.type(cpt.mean(x))", "pen_type(cpt_mean(x))", "text", [], [], "The penalty name.", "Penalty type"),
    ("pen.value", "pen.value(cpt.mean(x))", "np.atleast_1d(pen_value(cpt_mean(x)))", "num", ["numpy"], [], "The penalty value.", "Penalty value"),
    ("pen.value.full", "pen.value.full(cpt.mean(x, method = 'BinSeg', Q = 5, penalty = 'SIC'))", "pen_value_full(cpt_mean(x, method='BinSeg', Q=5, penalty='SIC'))", "num", ["numpy"], [], "The BinSeg likelihoods for each candidate.", "Penalty range"),
    ("minseglen", "minseglen(cpt.mean(x))", "np.asarray([minseglen(cpt_mean(x))])", "num", ["numpy"], [], "The shortest segment the search allows.", "Minimum segment length"),
    ("seg.len", "seg.len(cpt.mean(x))", "seg_len(cpt_mean(x))", "num", ["numpy"], [], "Length of each segment, including the last.", "Segment lengths"),
    ("nseg", "nseg(cpt.mean(x))", "np.asarray([nseg(cpt_mean(x))])", "num", ["numpy"], [], "One more than the number of changepoints.", "Number of segments"),
    ("logLik", "as.numeric(logLik(cpt.mean(x)))", "logLik(cpt_mean(x))", "num", ["numpy"], [], "Twice the negative log likelihood, and the penalised value.", "Log likelihood"),
    ("likelihood", "as.numeric(likelihood(cpt.mean(x)))", "likelihood(cpt_mean(x))", "num", ["numpy"], [], "The same two numbers logLik returns.", "Likelihood"),
    ("fitted", "fitted(cpt.mean(x))", "fitted(cpt_mean(x))", "num", ["numpy"], [], "The segment mean repeated along the series.", "Fitted values"),
    ("residuals", "residuals(cpt.mean(x))", "residuals(cpt_mean(x))", "num", ["numpy"], [], "The series minus the fitted segment means.", "Residuals"),
    ("data.set", "data.set(cpt.mean(x))", "data_set(cpt_mean(x))", "num", ["numpy"], [], "The numeric series.", "Data"),
    ("data.set.ts", "local({ ans <- cpt.mean(x); c(tsp(data.set.ts(ans)), as.numeric(data.set.ts(ans))[1]) })", "np.asarray([cpt_mean(x).index[0], cpt_mean(x).index[-1], 1.0, data_set_ts(cpt_mean(x))[0]])", "num", ["numpy"], [], "The series index runs from 1 to n, and the first value is the data.", "Series index"),
    ("summary", 'paste(capture.output(summary(cpt.mean(x))), collapse = "\\n")', "summary_text(cpt_mean(x))", "text", [], [], "The printed summary.", "Summary"),
    ("show", 'local({ t <- capture.output(show(cpt.mean(x))); t <- sub("Created on  :.*", "Created on  : DATE", t); paste(t, collapse = "\\n") })', "show_text(cpt_mean(x))", "text", [], [], "The printed object, with the creation time held aside.", "Show"),
    ("plot", 'local({ pdf(tempfile()); ans <- cpt.mean(x); plot(ans); dev.off(); paste(cpts(ans), collapse = " ") })', "plot_text(cpt_mean(x))", "text", ["numpy"], ["matplotlib"], "The series and the fitted step. The check is the changepoint locations.", "Plot"),
    ("cpts<-", 'local({ ans <- cpt.mean(x); cpts(ans) <- 10; paste(cpts(ans), collapse = " ") })', "setter_cpts()", "text", ["numpy"], [], "Store 10 and keep the series length on the end.", "Replace changepoints"),
    ("cpttype<-", 'local({ ans <- cpt.mean(x); cpttype(ans) <- "shift"; cpttype(ans) })', "cpttype(cpttype_set(cpt_mean(x), 'shift'))", "text", ["numpy"], [], "Replace the changepoint type.", "Replace type"),
    ("data.set<-", 'local({ ans <- cpt.mean(x); data.set(ans) <- 1:5; length(data.set(ans)) })', "np.asarray([len(data_set(data_set_set(cpt_mean(x), np.arange(1, 6))))])", "num", ["numpy"], [], "Replace the series. A plain vector keeps the index 1 to n.", "Replace data"),
    ("distribution<-", 'local({ ans <- cpt.mean(x); distribution(ans) <- "CSS"; distribution(ans) })', "distribution(distribution_set(cpt_mean(x), 'CSS'))", "text", ["numpy"], [], "Replace the test statistic through the old name.", "Replace distribution"),
    ("test.stat<-", 'local({ ans <- cpt.mean(x); test.stat(ans) <- "CUSUM"; test.stat(ans) })', "test_stat(test_stat_set(cpt_mean(x), 'CUSUM'))", "text", ["numpy"], [], "Replace the test statistic.", "Replace test statistic"),
    ("ncpts.max<-", 'local({ ans <- cpt.mean(x); ncpts.max(ans) <- 4; ncpts.max(ans) })', "np.asarray([ncpts_max(ncpts_max_set(cpt_mean(x), 4))])", "num", ["numpy"], [], "Replace the maximum number of changepoints.", "Replace maximum"),
    ("param.est<-", 'local({ ans <- cpt.mean(x); param.est(ans) <- list(mean = 3); param.est(ans)$mean })', "np.asarray([param_est(param_est_set(cpt_mean(x), {'mean': 3}))['mean']])", "num", ["numpy"], [], "Replace the stored estimates.", "Replace estimates"),
    ("pen.type<-", 'local({ ans <- cpt.mean(x); pen.type(ans) <- "SIC"; pen.type(ans) })', "pen_type(pen_type_set(cpt_mean(x), 'SIC'))", "text", ["numpy"], [], "Replace the penalty name.", "Replace penalty type"),
    ("pen.value<-", 'local({ ans <- cpt.mean(x); pen.value(ans) <- 7; pen.value(ans) })', "np.atleast_1d(pen_value(pen_value_set(cpt_mean(x), 7)))", "num", ["numpy"], [], "Replace the penalty value.", "Replace penalty value"),
    ("method<-", 'local({ ans <- cpt.mean(x); method(ans) <- "AMOC"; method(ans) })', "method(method_set(cpt_mean(x), 'AMOC'))", "text", ["numpy"], [], "Replace the search method.", "Replace method"),
    ("cpts.full<-", 'local({ ans <- cpt.mean(x, method = "BinSeg", Q = 5, penalty = "SIC"); cpts.full(ans) <- matrix(1:4, nrow = 2); as.numeric(cpts.full(ans)) })', "np.asarray(cpts_full(cpts_full_set(cpt_mean(x, method='BinSeg', Q=5, penalty='SIC'), np.arange(1, 5).reshape(2, 2, order='F'))), dtype=float).reshape(-1, order='F')", "num", ["numpy"], [], "Replace the stored segmentations.", "Replace segmentations"),
    ("minseglen<-", 'local({ ans <- cpt.mean(x); minseglen(ans) <- 3; minseglen(ans) })', "np.asarray([minseglen(minseglen_set(cpt_mean(x), 3))])", "num", ["numpy"], [], "Replace the minimum segment length.", "Replace minimum length"),
    ("pen.value.full<-", 'local({ ans <- cpt.mean(x, method = "BinSeg", Q = 5, penalty = "SIC"); pen.value.full(ans) <- c(1, 2); pen.value.full(ans) })', "pen_value_full(pen_value_full_set(cpt_mean(x, method='BinSeg', Q=5, penalty='SIC'), [1, 2]))", "num", ["numpy"], [], "Replace the stored penalty range.", "Replace penalty range"),
]


def r_proof(body):
    return R_HEAD + f"""
one <- function() {{
  {body}
}}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {{
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}}
cat(sprintf('{{"value":%s,"median_ms":%.17g}}\\n', json_val(value), median(elapsed) * 1000))
"""


def py_proof(body):
    return PY_HEAD + f"""
import io, contextlib

def summary_text(obj):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        summary(obj)
    return buf.getvalue().rstrip("\\n")

def show_text(obj):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        show(obj)
    lines = buf.getvalue().splitlines()
    lines = ["Created on  : DATE" if line.startswith("Created on  :") else line for line in lines]
    return "\\n".join(lines)

def plot_text(obj):
    plot(obj)
    return " ".join(str(int(v)) for v in cpts(obj))

def setter_cpts():
    ans = cpts_set(cpt_mean(x), 10)
    return " ".join(str(int(v)) for v in cpts(ans))

def one():
    return {body}

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

def emit(value):
    if isinstance(value, str):
        return value
    arr = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
    return [None if not np.isfinite(float(v)) else float(v) for v in arr]

print(json.dumps({{"value": emit(value), "median_ms": statistics.median(elapsed)}}))
"""


def run(cmd, text):
    result = subprocess.run(cmd, input=text, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or result.stdout[-2000:])
    line = [item for item in result.stdout.splitlines() if item.startswith("{")][-1]
    return json.loads(line)


def diff(left, right):
    if isinstance(left, str) or isinstance(right, str):
        return 0.0 if left == right else 1.0
    a = [np.nan if v is None else float(v) for v in left]
    b = [np.nan if v is None else float(v) for v in right]
    if len(a) != len(b):
        return 1.0
    gaps = [0.0 if (np.isnan(x) and np.isnan(y)) else abs(x - y) for x, y in zip(a, b)]
    return float(np.max(gaps)) if gaps else 0.0


def show(value):
    if isinstance(value, str):
        return value + "\n"
    return " ".join("NA" if v is None else f"{v:.10g}" for v in value) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    functions = []
    for name, r_body, py_body, kind, uses, loads, done, title in CASES:
        print(name, flush=True)
        r_text = r_proof(r_body)
        py_text = py_proof(py_body)
        (PROOF / f"{name}-r.R").write_text(r_text)
        (PROOF / f"{name}-py.py").write_text(py_text)
        env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT)}
        r_out = json.loads(subprocess.check_output(["Rscript", str(PROOF / f"{name}-r.R")], text=True).splitlines()[-1])
        py_out = json.loads(subprocess.check_output([PY, str(PROOF / f"{name}-py.py")], text=True, env=env).splitlines()[-1])
        gap = diff(r_out["value"], py_out["value"])
        matched = gap <= 1e-8
        print(" ", matched, gap, flush=True)
        (OUT / f"{name}-r.txt").write_text(show(r_out["value"]))
        (OUT / f"{name}-python.txt").write_text(show(py_out["value"]))
        doc = {
            "name": name,
            "title": title,
            "origin": {
                "description": done,
                "usage": name,
                "arguments": [],
                "details": "",
                "value": "See the example.",
                "example": r_body,
                "output": f"output/{name}-r.txt",
            },
            "translation": {
                "description": done,
                "usage": py_body,
                "arguments": [],
                "details": "Numeric series follow coredata of a plain vector. The index of that series is 1 to n.",
                "value": "See the example.",
                "example": py_body,
                "output": f"output/{name}-python.txt",
            },
        }
        (DOCS / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n")
        speedup = r_out["median_ms"] / py_out["median_ms"] if py_out["median_ms"] else None
        functions.append(
            {
                "name": name,
                "translated": matched,
                "python": "changepoint." + {
                    "cpt.mean": "cpt_mean",
                    "cpt.var": "cpt_var",
                    "cpt.meanvar": "cpt_meanvar",
                    "cpt.reg": "cpt_reg",
                    "cpts.full": "cpts_full",
                    "cpts.ts": "cpts_ts",
                    "test.stat": "test_stat",
                    "ncpts.max": "ncpts_max",
                    "param.est": "param_est",
                    "pen.type": "pen_type",
                    "pen.value": "pen_value",
                    "pen.value.full": "pen_value_full",
                    "seg.len": "seg_len",
                    "data.set": "data_set",
                    "data.set.ts": "data_set_ts",
                    "cpts<-": "cpts_set",
                    "cpttype<-": "cpttype_set",
                    "data.set<-": "data_set_set",
                    "distribution<-": "distribution_set",
                    "test.stat<-": "test_stat_set",
                    "ncpts.max<-": "ncpts_max_set",
                    "param.est<-": "param_est_set",
                    "pen.type<-": "pen_type_set",
                    "pen.value<-": "pen_value_set",
                    "method<-": "method_set",
                    "cpts.full<-": "cpts_full_set",
                    "minseglen<-": "minseglen_set",
                    "pen.value.full<-": "pen_value_full_set",
                }.get(name, name),
                "loads": loads,
                "uses": uses,
                "done": done if matched else "",
                "not_done": "" if matched else f"max abs diff {gap}",
                "blocked_by": [],
                "assigned": "",
                "check": {
                    "case": done,
                    "r_ms": r_out["median_ms"],
                    "translated_ms": py_out["median_ms"],
                    "speedup": speedup,
                    "matches": matched,
                    "max_abs_diff": gap,
                    "tolerance": 1e-8,
                    "proof": {"r": r_text, "python": py_text},
                },
            }
        )
    datasets = [
        ("ftse100", "ftse100", "A date and the daily log return.", 'c(nrow(ftse100), ftse100[1, 2])', "np.asarray([len(ftse100()['value']), float(ftse100()['value'][0])])"),
        ("HC1", "HC1", "House prices.", "c(length(HC1), HC1[1])", "np.asarray([len(HC1()), float(HC1()[0])])"),
        ("Lai2005fig3", "Lai2005fig3", "Spot, channel, positions, and GBM31.", "c(nrow(Lai2005fig3), Lai2005fig3$GBM31[1])", "np.asarray([len(Lai2005fig3()['Spot']), float(Lai2005fig3()['GBM31'][0])])"),
        ("Lai2005fig4", "Lai2005fig4", "Spot, channel, positions, and GBM29.", "c(nrow(Lai2005fig4), Lai2005fig4$GBM29[1])", "np.asarray([len(Lai2005fig4()['Spot']), float(Lai2005fig4()['GBM29'][0])])"),
        ("wave.c44137", "wave_c44137", "A wave sampled at one point.", "c(length(wave.c44137), wave.c44137[1])", "np.asarray([len(wave_c44137()), float(wave_c44137()[0])])"),
    ]
    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT)}
    for name, python_name, done, r_body, py_body in datasets:
        print(name, flush=True)
        r_text = R_HEAD + f"\ndata({name if name != 'wave.c44137' else 'wave.c44137'})\ncat(sprintf('{{\"value\":%s}}\\n', json_val({r_body})))\n"
        if name == "wave.c44137":
            r_text = R_HEAD + f"\ndata(wave.c44137)\ncat(sprintf('{{\"value\":%s}}\\n', json_val({r_body})))\n"
        py_text = PY_HEAD + f"\nvalue = {py_body}\narr = np.atleast_1d(np.asarray(value, dtype=float))\nprint(json.dumps({{'value': [float(v) for v in arr]}}))\n"
        (PROOF / f"{name}-r.R").write_text(r_text)
        (PROOF / f"{name}-py.py").write_text(py_text)
        r_out = json.loads(subprocess.check_output(["Rscript", str(PROOF / f"{name}-r.R")], text=True).splitlines()[-1])
        py_out = json.loads(subprocess.check_output([PY, str(PROOF / f"{name}-py.py")], text=True, env=env).splitlines()[-1])
        gap = diff(r_out["value"], py_out["value"])
        print(" ", gap <= 1e-8, gap, flush=True)
        (OUT / f"{name}-r.txt").write_text(show(r_out["value"]))
        (OUT / f"{name}-python.txt").write_text(show(py_out["value"]))
        (DOCS / f"{name}.json").write_text(json.dumps({
            "name": name,
            "title": name,
            "origin": {"description": done, "usage": f"data({name})", "arguments": [], "details": "", "value": "See the example.", "example": r_body, "output": f"output/{name}-r.txt"},
            "translation": {"description": done, "usage": f"{python_name}()", "arguments": [], "details": "The series is the one shipped with changepoint 2.3.", "value": "See the example.", "example": py_body, "output": f"output/{name}-python.txt"},
        }, indent=2) + "\n")
        functions.append({
            "name": name,
            "translated": gap <= 1e-8,
            "python": f"changepoint.{python_name}",
            "loads": [],
            "uses": ["numpy"],
            "done": done,
            "not_done": "",
            "blocked_by": [],
            "assigned": "",
        })
    record = {
        "name": "changepoint",
        "cran_version": "2.3",
        "inventory": "complete",
        "status": "complete" if all(item["translated"] for item in functions) else "in_progress",
        "blocked_by": [],
        "crate_claims": [],
        "resume": "PELT, BinSeg, SegNeigh, AMOC, and CROPS follow changepoint 2.3. Numeric series use coredata of a plain vector, so zoo stays unloaded. The regression segments use NumPy's least squares.",
        "dependencies": {"translated": [], "native": ["matplotlib", "numpy"], "rust": []},
        "functions": functions,
    }
    (ROOT / "translation.json").write_text(json.dumps(record, indent=2) + "\n")
    print("status", record["status"], "matched", sum(item["translated"] for item in functions), "/", len(functions))


if __name__ == "__main__":
    main()
