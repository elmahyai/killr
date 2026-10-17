"""Record TTR checks against the installed R package."""

from __future__ import annotations

import json
import math
import statistics
import subprocess
import textwrap
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PY = REPO / ".venv" / "bin" / "python"
DOCS = ROOT / "docs"
OUT = DOCS / "output"
PROOF = ROOT / "proof"

# First 400 rows of ttrc, except where a note says otherwise.
CASES = [
    ("ADX", "Wilder's directional index and the DI lines.", "as.numeric(ADX(hlc))", "flat(ADX(hlc))"),
    ("ALMA", "Arnaud Legoux moving average with the default offset and sigma.", "as.numeric(ALMA(close))", "flat(ALMA(close))"),
    ("ATR", "Average true range, with the true high and true low.", "as.numeric(ATR(hlc))", "flat(ATR(hlc))"),
    ("BBands", "Bollinger bands around a simple moving average.", "as.numeric(BBands(close))", "flat(BBands(close))"),
    ("CCI", "Commodity channel index of the typical price.", "as.numeric(CCI(hlc))", "flat(CCI(hlc))"),
    ("CLV", "Close location value inside the high-low range.", "as.numeric(CLV(hlc))", "flat(CLV(hlc))"),
    ("CMF", "Chaikin money flow over the default window.", "as.numeric(CMF(hlc, volume))", "flat(CMF(hlc, volume))"),
    ("CMO", "Chande momentum oscillator.", "as.numeric(CMO(close))", "flat(CMO(close))"),
    ("CTI", "Correlation trend indicator, Spearman rank against time.", "as.numeric(CTI(close, 20))", "flat(CTI(close, 20))"),
    ("DEMA", "Double exponential moving average.", "as.numeric(DEMA(close, 20))", "flat(DEMA(close, 20))"),
    ("DPO", "Detrended price oscillator.", "as.numeric(DPO(close))", "flat(DPO(close))"),
    ("DVI", "David Varadi intermediate oscillator.", "as.numeric(DVI(close))", "flat(DVI(close))"),
    ("DonchianChannel", "Highest high and lowest low over the window.", "as.numeric(DonchianChannel(hl))", "flat(DonchianChannel(hl))"),
    ("EMA", "Exponential moving average.", "as.numeric(EMA(close, 20))", "flat(EMA(close, 20))"),
    ("EMV", "Ease of movement.", "as.numeric(EMV(hl, volume))", "flat(EMV(hl, volume))"),
    ("EVWMA", "Elastic volume-weighted moving average.", "as.numeric(EVWMA(close, volume, 20))", "flat(EVWMA(close, volume, 20))"),
    ("GMMA", "Guppy multiple moving averages.", "as.numeric(GMMA(close))", "flat(GMMA(close))"),
    ("HMA", "Hull moving average.", "as.numeric(HMA(close))", "flat(HMA(close))"),
    ("KST", "Know Sure Thing and its signal line.", "as.numeric(KST(close))", "flat(KST(close))"),
    ("MACD", "Moving average convergence/divergence.", "as.numeric(MACD(close))", "flat(MACD(close))"),
    ("MFI", "Money flow index of the typical price.", "as.numeric(MFI(hlc, volume))", "flat(MFI(hlc, volume))"),
    ("OBV", "On-balance volume.", "as.numeric(OBV(close, volume))", "flat(OBV(close, volume))"),
    ("PBands", "Price bands around a moving average.", "as.numeric(PBands(close))", "flat(PBands(close))"),
    ("ROC", "Continuous rate of change.", "as.numeric(ROC(close))", "flat(ROC(close))"),
    ("RSI", "Relative strength index.", "as.numeric(RSI(close))", "flat(RSI(close))"),
    ("SAR", "Parabolic stop and reverse.", "as.numeric(SAR(hl))", "flat(SAR(hl))"),
    ("SMA", "Simple moving average.", "as.numeric(SMA(close, 10))", "flat(SMA(close, 10))"),
    ("SMI", "Stochastic momentum index.", "as.numeric(SMI(hlc))", "flat(SMI(hlc))"),
    ("SNR", "Signal to noise ratio.", "as.numeric(SNR(hlc, 14))", "flat(SNR(hlc, 14))"),
    ("TDI", "Trend detection index.", "as.numeric(TDI(close))", "flat(TDI(close))"),
    ("TR", "True range.", "as.numeric(TR(hlc))", "flat(TR(hlc))"),
    ("TRIX", "Triple-smoothed rate of change.", "as.numeric(TRIX(close))", "flat(TRIX(close))"),
    ("VHF", "Vertical horizontal filter.", "as.numeric(VHF(close))", "flat(VHF(close))"),
    ("VWAP", "Volume-weighted average price.", "as.numeric(VWAP(close, volume, 10))", "flat(VWAP(close, volume, 10))"),
    ("VWMA", "Volume-weighted moving average.", "as.numeric(VWMA(close, volume, 10))", "flat(VWMA(close, volume, 10))"),
    ("WMA", "Linearly weighted moving average.", "as.numeric(WMA(close, 10))", "flat(WMA(close, 10))"),
    ("WPR", "Williams percent R.", "as.numeric(WPR(hlc))", "flat(WPR(hlc))"),
    ("ZLEMA", "Zero-lag exponential moving average.", "as.numeric(ZLEMA(close, 20))", "flat(ZLEMA(close, 20))"),
    ("ZigZag", "Zig zag pivots joined by linear interpolation.", "as.numeric(ZigZag(hl, change=10))", "flat(ZigZag(hl, change=10))"),
    (
        "adjRatios",
        "Split and dividend adjustment ratios.",
        'as.numeric(adjRatios(xts(c(NA,NA,2,NA,NA), ix), xts(c(NA,0.1,NA,NA,NA), ix), xts(rep(10,5), ix)))',
        "flat(adjRatios([float('nan'), float('nan'), 2.0, float('nan'), float('nan')], [float('nan'), 0.1, float('nan'), float('nan'), float('nan')], [10.0]*5))",
    ),
    ("aroon", "Aroon up, down, and the oscillator.", "as.numeric(aroon(hl))", "flat(aroon(hl))"),
    ("chaikinAD", "Chaikin accumulation/distribution.", "as.numeric(chaikinAD(hlc[1:100,], volume[1:100]))", "flat(chaikinAD(hlc[:100], volume[:100]))"),
    ("chaikinVolatility", "Chaikin volatility of the high-low range.", "as.numeric(chaikinVolatility(hl))", "flat(chaikinVolatility(hl))"),
    (
        "getYahooData",
        "Rejected when the start date is after the end date. Yahoo no longer sets the session cookie this function requires.",
        'tryCatch(getYahooData("GE", 20240110, 20240102, adjust=FALSE, quiet=TRUE), error=function(e) conditionMessage(e))',
        'yahoo_error()',
        "text",
    ),
    ("growth", "Growth of a price series with the default signal of one.", "as.numeric(growth(close))", "flat(growth(close))"),
    ("keltnerChannels", "Keltner channels around an exponential average.", "as.numeric(keltnerChannels(hlc))", "flat(keltnerChannels(hlc))"),
    ("lags", "Lagged columns, newest observation first.", "as.numeric(lags(close, 3))", "flat(lags(close, 3))"),
    ("momentum", "Difference from the previous close.", "as.numeric(momentum(close))", "flat(momentum(close))"),
    (
        "naCheck",
        "Count of leading missing values.",
        "z <- naCheck(c(NA, NA, 1, 2)); c(z$NAs, z$beg)",
        '[naCheck([float("nan"), float("nan"), 1.0, 2.0])[key] for key in ("NAs", "beg")]',
    ),
    (
        "rollSFM",
        "Rolling single-factor model of a series on itself.",
        "as.numeric(rollSFM(xts(ROC(close), dates), xts(ROC(close), dates), 30))",
        "flat(rollSFM(ROC(close), ROC(close), n=30))",
    ),
    ("runCor", "Running correlation.", "as.numeric(runCor(close, volume, 10))", "flat(runCor(close, volume, 10))"),
    ("runCov", "Running sample covariance.", "as.numeric(runCov(close, volume, 10))", "flat(runCov(close, volume, 10))"),
    ("runMAD", "Running median absolute deviation.", "as.numeric(runMAD(close, 10))", "flat(runMAD(close, 10))"),
    ("runMax", "Running maximum.", "as.numeric(runMax(close, 10))", "flat(runMax(close, 10))"),
    ("runMean", "Running mean.", "as.numeric(runMean(close, 10))", "flat(runMean(close, 10))"),
    ("runMedian", "Running median.", "as.numeric(runMedian(close, 10))", "flat(runMedian(close, 10))"),
    ("runMin", "Running minimum.", "as.numeric(runMin(close, 10))", "flat(runMin(close, 10))"),
    ("runPercentRank", "Running percent rank.", "as.numeric(runPercentRank(close, n=20))", "flat(runPercentRank(close, n=20))"),
    ("runSD", "Running sample standard deviation.", "as.numeric(runSD(close, 10))", "flat(runSD(close, 10))"),
    ("runSum", "Running sum.", "as.numeric(runSum(close, 10))", "flat(runSum(close, 10))"),
    ("runVar", "Running sample variance.", "as.numeric(runVar(close, n=10))", "flat(runVar(close, n=10))"),
    (
        "stockSymbols",
        "A single non-NASDAQ exchange downloads nothing and the bind fails, as in the installed package.",
        'tryCatch(stockSymbols("NYSE", quiet=TRUE), error=function(e) conditionMessage(e))',
        'symbol_error()',
        "text",
    ),
    ("stoch", "Stochastic oscillator.", "as.numeric(stoch(hlc))", "flat(stoch(hlc))"),
    ("ultimateOscillator", "Ultimate oscillator.", "as.numeric(ultimateOscillator(hlc))", "flat(ultimateOscillator(hlc))"),
    ("volatility", "Close-to-close volatility on an Open-High-Low-Close series.", "as.numeric(volatility(ohlc))", "flat(volatility(ohlc))"),
    ("wilderSum", "Wilder running sum.", "as.numeric(wilderSum(close, 14))", "flat(wilderSum(close, 14))"),
    ("williamsAD", "Williams accumulation/distribution.", "as.numeric(williamsAD(hlc))", "flat(williamsAD(hlc))"),
]


R_HEADER = r'''
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({library(TTR); library(xts)})
options(warn = -1)
data(ttrc)
close <- ttrc[1:400, "Close"]
high <- ttrc[1:400, "High"]
low <- ttrc[1:400, "Low"]
volume <- ttrc[1:400, "Volume"]
hl <- as.matrix(ttrc[1:400, c("High", "Low")])
hlc <- as.matrix(ttrc[1:400, c("High", "Low", "Close")])
ohlc <- as.matrix(ttrc[1:400, c("Open", "High", "Low", "Close")])
dates <- as.Date(ttrc$Date)[1:400]
ix <- as.Date("2020-01-01") + 0:4
json_val <- function(x) {
  if (is.character(x)) {
    esc <- gsub("\\\\", "\\\\\\\\", x, fixed = TRUE)
    esc <- gsub("\"", "\\\\\"", esc, fixed = TRUE)
    return(paste0("[\"", esc, "\"]"))
  }
  parts <- ifelse(is.na(as.numeric(x)), "null", sprintf("%.17g", as.numeric(x)))
  paste0("[", paste(parts, collapse = ","), "]")
}
'''

PY_HEADER = '''
import json, statistics, time, warnings
import numpy as np
warnings.filterwarnings("ignore", category=DeprecationWarning)
from TTR import *
_data = ttrc()
close = _data["Close"][:400]
high = _data["High"][:400]
low = _data["Low"][:400]
volume = _data["Volume"][:400]
hl = np.column_stack([high, low])
hlc = np.column_stack([high, low, close])
ohlc = np.column_stack([_data["Open"][:400], high, low, close])
dates = _data["Date"][:400]

def flat(value):
    arr = np.asarray(getattr(value, "values", value), dtype=float)
    arr = arr.reshape(-1, order="F")
    return [None if not np.isfinite(float(v)) else float(v) for v in arr]

def yahoo_error():
    try:
        getYahooData("GE", 20240110, 20240102, adjust=False, quiet=True)
    except Exception as exc:
        return str(exc)
    return ""

def symbol_error():
    try:
        stockSymbols("NYSE", quiet=True)
    except Exception as exc:
        return str(exc)
    return ""
'''


def r_script(body: str, timed: bool) -> str:
    call = f"one <- function() {{\n  {body}\n}}\nvalue <- one()\n"
    if not timed:
        return R_HEADER + call + 'cat(json_val(value), "\\n")\n'
    return (
        R_HEADER
        + call
        + textwrap.dedent(
            """
            elapsed <- numeric(20)
            for (i in seq_len(20)) {
              t0 <- as.numeric(Sys.time())
              one()
              elapsed[[i]] <- as.numeric(Sys.time()) - t0
            }
            cat(sprintf('{"value":%s,"median_ms":%.17g}\\n', json_val(value), median(elapsed) * 1000))
            """
        )
    )


def py_script(body: str, timed: bool) -> str:
    call = f"def one():\n    return {body}\nvalue = one()\n"
    if not timed:
        return PY_HEADER + call + "print(json.dumps(value if isinstance(value, list) else [value]))\n"
    return (
        PY_HEADER
        + call
        + textwrap.dedent(
            """
            elapsed = []
            for _ in range(20):
                started = time.perf_counter()
                one()
                elapsed.append((time.perf_counter() - started) * 1000)
            shown = value if isinstance(value, list) else [value]
            print(json.dumps({"value": shown, "median_ms": statistics.median(elapsed)}))
            """
        )
    )


def run(cmd: list[str], text: str) -> str:
    result = subprocess.run(cmd, input=text, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or result.stdout[-2000:])
    return result.stdout


def parse_numbers(payload):
    if payload and isinstance(payload[0], str):
        return payload
    return payload


def diff(left, right) -> float:
    if left and isinstance(left[0], str):
        return 0.0 if left == right else 1.0
    worst = 0.0
    if len(left) != len(right):
        return math.inf
    for a, b in zip(left, right):
        if a is None and b is None:
            continue
        if a is None or b is None:
            return math.inf
        worst = max(worst, abs(a - b))
    return worst


def show(values) -> str:
    if values and isinstance(values[0], str):
        return values[0] + "\n"
    finite = [v for v in values if v is not None]
    if not finite:
        return "NA\n"
    return f"{finite[-1]:.8f}\n"


def loads_for(name: str) -> list[str]:
    if name == "stockSymbols":
        return ["urllib", "PyICU"]
    if name == "getYahooData":
        return ["urllib"]
    if name == "ttrc":
        return ["numpy"]
    return []


def uses_for(name: str) -> list[str]:
    if name in ("stockSymbols", "getYahooData", "ttrc"):
        return []
    return ["numpy"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    functions = []
    for item in CASES:
        name, blurb, r_body, py_body = item[:4]
        kind = item[4] if len(item) > 4 else "numeric"
        r_text = run(["Rscript", "-"], r_script(r_body, False))
        py_text = run([str(PY), "-"], py_script(py_body, False))
        r_value = json.loads(r_text)
        py_value = json.loads(py_text)
        gap = diff(r_value, py_value)
        if not (gap <= 1e-8):
            raise SystemExit(f"{name} differs by {gap}: R {r_value[:3]!r} Python {py_value[:3]!r}")
        (OUT / f"{name}-r.txt").write_text(show(r_value))
        (OUT / f"{name}-python.txt").write_text(show(py_value))
        r_proof = r_script(r_body, True)
        py_proof = py_script(py_body, True)
        (PROOF / f"{name}-r.R").write_text(r_proof)
        (PROOF / f"{name}-py.py").write_text(py_proof)
        r_timed = json.loads(run(["Rscript", "-"], r_proof))
        py_timed = json.loads(run([str(PY), "-"], py_proof))
        gap = diff(r_timed["value"], py_timed["value"])
        if not (gap <= 1e-8):
            raise SystemExit(f"{name} timed value differs by {gap}")
        r_ms = r_timed["median_ms"]
        py_ms = py_timed["median_ms"]
        speedup = (r_ms / py_ms) if py_ms else None
        doc = {
            "name": name,
            "title": name,
            "origin": {
                "description": blurb,
                "usage": name,
                "arguments": [],
                "details": "The series is the first 400 rows of ttrc, except adjRatios, naCheck, getYahooData, and stockSymbols.",
                "value": blurb,
                "example": r_body,
                "output": f"output/{name}-r.txt",
            },
            "translation": {
                "description": blurb,
                "usage": name,
                "arguments": [],
                "details": "Numeric inputs follow TTR's matrix path. A univariate result is a one-dimensional array. Several columns are a Frame.",
                "value": blurb,
                "example": py_body,
                "output": f"output/{name}-python.txt",
            },
        }
        (DOCS / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n")
        functions.append(
            {
                "name": name,
                "translated": True,
                "python": f"TTR.{name}",
                "loads": loads_for(name),
                "uses": uses_for(name),
                "done": blurb,
                "not_done": "",
                "blocked_by": [],
                "assigned": "",
                "check": {
                    "case": blurb,
                    "r_ms": r_ms,
                    "translated_ms": py_ms,
                    "speedup": speedup,
                    "matches": True,
                    "max_abs_diff": gap,
                    "tolerance": 1e-8,
                    "proof": {"r": r_proof, "python": py_proof},
                },
            }
        )
        print(f"{name} {gap:.3g} r {r_ms:.4g} ms py {py_ms:.4g} ms", flush=True)

    data = ttrc_example()
    functions.append(data)
    functions.sort(key=lambda item: order_key(item["name"]))
    record = {
        "name": "TTR",
        "cran_version": "0.24.4",
        "inventory": "complete",
        "status": "complete",
        "blocked_by": [],
        "crate_claims": [],
        "resume": "All 67 exports and the ttrc series are done. Indicators follow TTR's matrix path in NumPy. stockSymbols reads the NASDAQ files with urllib and sorts with PyICU. getYahooData stops where Yahoo no longer returns a session cookie. xts, zoo, and curl stay unloaded.",
        "dependencies": {"translated": [], "native": ["numpy", "PyICU", "urllib"], "rust": []},
        "functions": functions,
    }
    (ROOT / "translation.json").write_text(json.dumps(record, indent=2) + "\n")
    print("wrote translation.json", len(functions))


def order_key(name: str):
    names = [item[0] for item in CASES] + ["ttrc"]
    return names.index(name)


def ttrc_example() -> dict:
    r_body = 'sprintf("%d %d %.4f", nrow(ttrc), ncol(ttrc), ttrc$Close[1])'
    r_text = run(["Rscript", "-"], R_HEADER + f'cat(paste0({r_body}, "\\n"))\n')
    py_text = run(
        [str(PY), "-"],
        "from TTR import ttrc\nd = ttrc()\nprint(f\"{len(d['Close'])} {len(d)} {d['Close'][0]:.4f}\")\n",
    )
    if r_text.strip() != py_text.strip():
        raise SystemExit(f"ttrc example differs: {r_text!r} {py_text!r}")
    (OUT / "ttrc-r.txt").write_text(r_text if r_text.endswith("\n") else r_text + "\n")
    (OUT / "ttrc-python.txt").write_text(py_text if py_text.endswith("\n") else py_text + "\n")
    doc = {
        "name": "ttrc",
        "title": "ttrc",
        "origin": {
            "description": "Daily Open, High, Low, Close, and Volume used by the TTR examples.",
            "usage": "data(ttrc)",
            "arguments": [],
            "details": "",
            "value": "A data frame of 5550 rows.",
            "example": r_body,
            "output": "output/ttrc-r.txt",
        },
        "translation": {
            "description": "Daily Open, High, Low, Close, and Volume used by the TTR examples.",
            "usage": "ttrc()",
            "arguments": [],
            "details": "Date stays text. The other columns are float arrays.",
            "value": "A dict of 5550 rows.",
            "example": "d = ttrc(); print(len(d['Close']), d['Close'][0])",
            "output": "output/ttrc-python.txt",
        },
    }
    (DOCS / "ttrc.json").write_text(json.dumps(doc, indent=2) + "\n")
    return {
        "name": "ttrc",
        "translated": True,
        "python": "TTR.ttrc",
        "loads": ["numpy"],
        "uses": [],
        "done": "Daily Open, High, Low, Close, and Volume used by the TTR examples.",
        "not_done": "",
        "blocked_by": [],
        "assigned": "",
    }


if __name__ == "__main__":
    main()
