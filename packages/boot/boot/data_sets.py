"""Tables from CRAN boot 1.3-32.

Each function returns one dataset. A numeric table is a NumPy array
paired with the R column names. Text and factor columns stay strings,
so those tables are lists of rows paired with the column names. A time
series is a one-dimensional array. cd4_nested returns the saved nested
bootstrap, and its replicate matrix is the entry t.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

_DATA = Path(__file__).resolve().parent / "data"


def _missing(cell: str):
    return cell == "NA" or cell == ""


def _read_numeric(name: str, columns: list[str]) -> tuple[list[str], np.ndarray]:
    path = _DATA / f"{name}.csv"
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != columns:
            raise ValueError(name)
        rows = [
            [float("nan") if _missing(cell) else float(cell) for cell in record]
            for record in reader
        ]
    return columns, np.array(rows, dtype=float)


def _read_mixed(
    name: str, columns: list[str], kinds: list[str]
) -> tuple[list[str], list[list]]:
    path = _DATA / f"{name}.csv"
    rows: list[list] = []
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != columns:
            raise ValueError(name)
        for record in reader:
            row = []
            for kind, cell in zip(kinds, record, strict=True):
                if _missing(cell):
                    row.append(None)
                elif kind == "float":
                    row.append(float(cell))
                elif kind == "int":
                    row.append(int(cell))
                else:
                    row.append(cell)
            rows.append(row)
    return columns, rows


def _read_matrix(name: str, width: int) -> np.ndarray:
    path = _DATA / f"{name}.csv"
    rows = []
    with path.open(newline="") as handle:
        for record in csv.reader(handle):
            if len(record) != width:
                raise ValueError(name)
            rows.append(
                [float("nan") if _missing(cell) else float(cell) for cell in record]
            )
    return np.array(rows, dtype=float)


def _read_series(name: str) -> np.ndarray:
    path = _DATA / f"{name}.csv"
    values = [float(line) for line in path.read_text().splitlines() if line]
    return np.array(values, dtype=float)


def _read_nested() -> dict:
    payload = json.loads((_DATA / "cd4.nested.json").read_text())
    return {
        "t0": np.array(payload["t0"], dtype=float),
        "t": np.array(payload["t"], dtype=float),
        "R": payload["R"],
        "data_columns": payload["data_columns"],
        "data": np.array(payload["data"], dtype=float),
        "seed": None,
        "statistic": payload["statistic"],
        "sim": payload["sim"],
        "call": payload["call"],
        "stype": payload["stype"],
        "strata": np.array(payload["strata"], dtype=float),
        "weights": np.array(payload["weights"], dtype=float),
    }


def acme():
    """Monthly Excess Returns"""
    return _read_mixed(
        "acme",
        ["month", "market", "acme"],
        ["str", "float", "float"],
    )

def aids():
    """Delay in AIDS Reporting in England and Wales"""
    return _read_numeric(
        "aids",
        ["year", "quarter", "delay", "dud", "time", "y"],
    )

def aircondit():
    """Failures of Air-conditioning Equipment"""
    columns = ["hours"]
    rows = np.array(
        [
            [3.0],
            [5.0],
            [7.0],
            [18.0],
            [43.0],
            [85.0],
            [91.0],
            [98.0],
            [100.0],
            [130.0],
            [230.0],
            [487.0],
        ]
    )
    return columns, rows

def aircondit7():
    """Failures of Air-conditioning Equipment"""
    columns = ["hours"]
    rows = np.array(
        [
            [3.0],
            [5.0],
            [5.0],
            [13.0],
            [14.0],
            [15.0],
            [22.0],
            [22.0],
            [23.0],
            [30.0],
            [36.0],
            [39.0],
            [44.0],
            [46.0],
            [50.0],
            [72.0],
            [79.0],
            [88.0],
            [97.0],
            [102.0],
            [139.0],
            [188.0],
            [197.0],
            [210.0],
        ]
    )
    return columns, rows

def amis():
    """Car Speeding and Warning Signs"""
    return _read_numeric(
        "amis",
        ["speed", "period", "warning", "pair"],
    )

def aml():
    """Remission Times for Acute Myelogenous Leukaemia"""
    columns = ["time", "cens", "group"]
    rows = np.array(
        [
            [9.0, 1.0, 1.0],
            [13.0, 1.0, 1.0],
            [13.0, 0.0, 1.0],
            [18.0, 1.0, 1.0],
            [23.0, 1.0, 1.0],
            [28.0, 0.0, 1.0],
            [31.0, 1.0, 1.0],
            [34.0, 1.0, 1.0],
            [45.0, 0.0, 1.0],
            [48.0, 1.0, 1.0],
            [161.0, 0.0, 1.0],
            [5.0, 1.0, 2.0],
            [5.0, 1.0, 2.0],
            [8.0, 1.0, 2.0],
            [8.0, 1.0, 2.0],
            [12.0, 1.0, 2.0],
            [16.0, 0.0, 2.0],
            [23.0, 1.0, 2.0],
            [27.0, 1.0, 2.0],
            [30.0, 1.0, 2.0],
            [33.0, 1.0, 2.0],
            [43.0, 1.0, 2.0],
            [45.0, 1.0, 2.0],
        ]
    )
    return columns, rows

def beaver():
    """Beaver Body Temperature Data"""
    return _read_numeric(
        "beaver",
        ["day", "time", "temp", "activ"],
    )

def bigcity():
    """Population of U.S. Cities"""
    return _read_numeric(
        "bigcity",
        ["u", "x"],
    )

def brambles():
    """Spatial Location of Bramble Canes"""
    return _read_numeric(
        "brambles",
        ["x", "y", "age"],
    )

def breslow():
    """Smoking Deaths Among Doctors"""
    columns = ["age", "smoke", "n", "y", "ns"]
    rows = [
            ["40", 0.0, 18790.0, 2.0, 0.0],
            ["50", 0.0, 10673.0, 12.0, 0.0],
            ["60", 0.0, 5710.0, 28.0, 0.0],
            ["70", 0.0, 2585.0, 28.0, 0.0],
            ["80", 0.0, 1462.0, 31.0, 0.0],
            ["40", 1.0, 52407.0, 32.0, 52407.0],
            ["50", 1.0, 43248.0, 104.0, 43248.0],
            ["60", 1.0, 28612.0, 206.0, 28612.0],
            ["70", 1.0, 12663.0, 186.0, 12663.0],
            ["80", 1.0, 5317.0, 102.0, 5317.0],
        ]
    return columns, rows

def calcium():
    """Calcium Uptake Data"""
    columns = ["time", "cal"]
    rows = np.array(
        [
            [0.45, 0.3417],
            [0.45, -0.00438],
            [0.45, 0.82531],
            [1.3, 1.77967],
            [1.3, 0.95384],
            [1.3, 0.6408],
            [2.4, 1.75136],
            [2.4, 1.27497],
            [2.4, 1.17332],
            [4.0, 3.12273],
            [4.0, 2.60958],
            [4.0, 2.57429],
            [6.1, 3.17881],
            [6.1, 3.00782],
            [6.1, 2.67061],
            [8.05, 3.05959],
            [8.05, 3.94321],
            [8.05, 3.43726],
            [11.15, 4.80735],
            [11.15, 3.35583],
            [11.15, 2.78309],
            [13.15, 5.13825],
            [13.15, 4.70274],
            [13.15, 4.25702],
            [15.0, 3.60407],
            [15.0, 4.15029],
            [15.0, 3.42484],
        ]
    )
    return columns, rows

def cane():
    """Sugar-cane Disease Data"""
    return _read_mixed(
        "cane",
        ["n", "r", "x", "var", "block"],
        ["float", "float", "float", "str", "str"],
    )

def capability():
    """Simulated Manufacturing Process Data"""
    return _read_numeric(
        "capability",
        ["y"],
    )

def catsM():
    """Weight Data for Domestic Cats"""
    return _read_mixed(
        "catsM",
        ["Sex", "Bwt", "Hwt"],
        ["str", "float", "float"],
    )

def cav():
    """Position of Muscle Caveolae"""
    return _read_numeric(
        "cav",
        ["x", "y"],
    )

def cd4():
    """CD4 Counts for HIV-Positive Patients"""
    columns = ["baseline", "oneyear"]
    rows = np.array(
        [
            [2.12, 2.47],
            [4.35, 4.61],
            [3.39, 5.26],
            [2.51, 3.02],
            [4.04, 6.36],
            [5.1, 5.93],
            [3.77, 3.93],
            [3.35, 4.09],
            [4.1, 4.88],
            [3.35, 3.81],
            [4.15, 4.74],
            [3.56, 3.29],
            [3.39, 5.55],
            [1.88, 2.82],
            [2.56, 4.23],
            [2.96, 3.23],
            [2.49, 2.56],
            [3.03, 4.31],
            [2.66, 4.37],
            [3.0, 2.4],
        ]
    )
    return columns, rows

def cd4_nested():
    """Nested Bootstrap of cd4 data"""
    return _read_nested()

def channing():
    """Channing House Data"""
    return _read_mixed(
        "channing",
        ["sex", "entry", "exit", "time", "cens"],
        ["str", "float", "float", "float", "float"],
    )

def city():
    """Population of U.S. Cities"""
    columns = ["u", "x"]
    rows = np.array(
        [
            [138.0, 143.0],
            [93.0, 104.0],
            [61.0, 69.0],
            [179.0, 260.0],
            [48.0, 75.0],
            [37.0, 63.0],
            [29.0, 50.0],
            [23.0, 48.0],
            [30.0, 111.0],
            [2.0, 50.0],
        ]
    )
    return columns, rows

def claridge():
    """Genetic Links to Left-handedness"""
    columns = ["dnan", "hand"]
    rows = np.array(
        [
            [13.0, 1.0],
            [18.0, 1.0],
            [20.0, 3.0],
            [21.0, 1.0],
            [21.0, 1.0],
            [24.0, 1.0],
            [24.0, 1.0],
            [27.0, 1.0],
            [28.0, 1.0],
            [28.0, 2.0],
            [28.0, 1.0],
            [28.0, 2.0],
            [28.0, 1.0],
            [28.0, 4.0],
            [28.0, 1.0],
            [28.0, 1.0],
            [29.0, 1.0],
            [29.0, 1.0],
            [29.0, 1.0],
            [29.0, 2.0],
            [29.0, 2.0],
            [29.0, 1.0],
            [29.0, 1.0],
            [30.0, 1.0],
            [30.0, 1.0],
            [30.0, 2.0],
            [30.0, 1.0],
            [31.0, 1.0],
            [31.0, 1.0],
            [31.0, 1.0],
            [31.0, 1.0],
            [31.0, 2.0],
            [33.0, 6.0],
            [33.0, 1.0],
            [34.0, 1.0],
            [41.0, 4.0],
            [44.0, 8.0],
        ]
    )
    return columns, rows

def cloth():
    """Number of Flaws in Cloth"""
    columns = ["x", "y"]
    rows = np.array(
        [
            [1.22, 1.0],
            [1.7, 4.0],
            [2.71, 5.0],
            [3.71, 14.0],
            [3.72, 7.0],
            [3.75, 9.0],
            [4.17, 2.0],
            [4.41, 8.0],
            [4.58, 4.0],
            [4.91, 7.0],
            [4.92, 4.0],
            [4.95, 7.0],
            [5.22, 6.0],
            [5.42, 9.0],
            [5.43, 8.0],
            [5.51, 6.0],
            [6.3, 7.0],
            [6.42, 10.0],
            [6.45, 6.0],
            [6.51, 4.0],
            [6.57, 9.0],
            [7.15, 14.0],
            [7.16, 3.0],
            [7.35, 17.0],
            [7.38, 9.0],
            [7.49, 10.0],
            [8.32, 17.0],
            [8.42, 9.0],
            [8.68, 8.0],
            [8.95, 28.0],
            [9.05, 23.0],
            [9.52, 9.0],
        ]
    )
    return columns, rows

def co_transfer():
    """Carbon Monoxide Transfer"""
    columns = ["entry", "week"]
    rows = np.array(
        [
            [40.0, 73.0],
            [50.0, 52.0],
            [56.0, 80.0],
            [58.0, 85.0],
            [60.0, 64.0],
            [62.0, 63.0],
            [66.0, 60.0],
        ]
    )
    return columns, rows

def coal():
    """Dates of Coal Mining Disasters"""
    return _read_numeric(
        "coal",
        ["date"],
    )

def darwin():
    """Darwin's Plant Height Differences"""
    columns = ["y"]
    rows = np.array(
        [
            [49.0],
            [-67.0],
            [8.0],
            [16.0],
            [6.0],
            [23.0],
            [28.0],
            [41.0],
            [14.0],
            [29.0],
            [56.0],
            [24.0],
            [75.0],
            [60.0],
            [-48.0],
        ]
    )
    return columns, rows

def dogs():
    """Cardiac Data for Domestic Dogs"""
    columns = ["mvo", "lvp"]
    rows = np.array(
        [
            [78.0, 32.0],
            [92.0, 33.0],
            [116.0, 45.0],
            [90.0, 30.0],
            [106.0, 38.0],
            [78.0, 24.0],
            [99.0, 44.0],
        ]
    )
    return columns, rows

def downs_bc():
    """Incidence of Down's Syndrome in British Columbia"""
    columns = ["age", "m", "r"]
    rows = np.array(
        [
            [17.0, 13555.0, 16.0],
            [18.5, 13675.0, 15.0],
            [19.5, 18752.0, 16.0],
            [20.5, 22005.0, 22.0],
            [21.5, 23896.0, 16.0],
            [22.5, 24667.0, 12.0],
            [23.5, 24807.0, 17.0],
            [24.5, 23986.0, 22.0],
            [25.5, 22860.0, 15.0],
            [26.5, 21450.0, 14.0],
            [27.5, 19202.0, 27.0],
            [28.5, 17450.0, 14.0],
            [29.5, 15685.0, 9.0],
            [30.5, 13954.0, 12.0],
            [31.5, 11987.0, 12.0],
            [32.5, 10983.0, 18.0],
            [33.5, 9825.0, 13.0],
            [34.5, 8483.0, 11.0],
            [35.5, 7448.0, 23.0],
            [36.5, 6628.0, 13.0],
            [37.5, 5780.0, 17.0],
            [38.5, 4834.0, 15.0],
            [39.5, 3961.0, 30.0],
            [40.5, 2952.0, 31.0],
            [41.5, 2276.0, 33.0],
            [42.4, 1589.0, 20.0],
            [43.5, 1018.0, 16.0],
            [44.5, 596.0, 22.0],
            [45.5, 327.0, 11.0],
            [47.0, 249.0, 7.0],
        ]
    )
    return columns, rows

def ducks():
    """Behavioral and Plumage Characteristics of Hybrid Ducks"""
    columns = ["plumage", "behaviour"]
    rows = np.array(
        [
            [7.0, 3.0],
            [13.0, 10.0],
            [14.0, 11.0],
            [6.0, 5.0],
            [14.0, 15.0],
            [15.0, 15.0],
            [4.0, 7.0],
            [8.0, 10.0],
            [7.0, 4.0],
            [9.0, 9.0],
            [14.0, 11.0],
        ]
    )
    return columns, rows

def fir():
    """Counts of Balsam-fir Seedlings"""
    return _read_mixed(
        "fir",
        ["count", "row", "col"],
        ["float", "int", "int"],
    )

def frets():
    """Head Dimensions in Brothers"""
    columns = ["l1", "b1", "l2", "b2"]
    rows = np.array(
        [
            [191.0, 155.0, 179.0, 145.0],
            [195.0, 149.0, 201.0, 152.0],
            [181.0, 148.0, 185.0, 149.0],
            [183.0, 153.0, 188.0, 149.0],
            [176.0, 144.0, 171.0, 142.0],
            [208.0, 157.0, 192.0, 152.0],
            [189.0, 150.0, 190.0, 149.0],
            [197.0, 159.0, 189.0, 152.0],
            [188.0, 152.0, 197.0, 159.0],
            [192.0, 150.0, 187.0, 151.0],
            [179.0, 158.0, 186.0, 148.0],
            [183.0, 147.0, 174.0, 147.0],
            [174.0, 150.0, 185.0, 152.0],
            [190.0, 159.0, 195.0, 157.0],
            [188.0, 151.0, 187.0, 158.0],
            [163.0, 137.0, 161.0, 130.0],
            [195.0, 155.0, 183.0, 158.0],
            [186.0, 153.0, 173.0, 148.0],
            [181.0, 145.0, 182.0, 146.0],
            [175.0, 140.0, 165.0, 137.0],
            [192.0, 154.0, 185.0, 152.0],
            [174.0, 143.0, 178.0, 147.0],
            [176.0, 139.0, 176.0, 143.0],
            [197.0, 167.0, 200.0, 158.0],
            [190.0, 163.0, 187.0, 150.0],
        ]
    )
    return columns, rows

def grav():
    """Acceleration Due to Gravity"""
    columns = ["g", "series"]
    rows = [
            [82.0, "7"],
            [79.0, "7"],
            [81.0, "7"],
            [79.0, "7"],
            [77.0, "7"],
            [79.0, "7"],
            [79.0, "7"],
            [78.0, "7"],
            [79.0, "7"],
            [82.0, "7"],
            [76.0, "7"],
            [73.0, "7"],
            [64.0, "7"],
            [84.0, "8"],
            [86.0, "8"],
            [85.0, "8"],
            [82.0, "8"],
            [77.0, "8"],
            [76.0, "8"],
            [77.0, "8"],
            [80.0, "8"],
            [83.0, "8"],
            [81.0, "8"],
            [78.0, "8"],
            [78.0, "8"],
            [78.0, "8"],
        ]
    return columns, rows

def gravity():
    """Acceleration Due to Gravity"""
    return _read_mixed(
        "gravity",
        ["g", "series"],
        ["float", "str"],
    )

def hirose():
    """Failure Time of PET Film"""
    return _read_numeric(
        "hirose",
        ["volt", "time", "cens"],
    )

def islay():
    """Jura Quartzite Azimuths on Islay"""
    columns = ["theta"]
    rows = np.array(
        [
            [12.0],
            [353.0],
            [359.0],
            [332.0],
            [341.0],
            [299.0],
            [30.0],
            [24.0],
            [53.0],
            [284.0],
            [99.0],
            [72.0],
            [28.0],
            [93.0],
            [125.0],
            [318.0],
            [3.0],
            [45.0],
        ]
    )
    return columns, rows

def manaus():
    """Average Heights of the Rio Negro river at Manaus"""
    return _read_series("manaus")

def melanoma():
    """Survival from Malignant Melanoma"""
    return _read_numeric(
        "melanoma",
        ["time", "status", "sex", "age", "year", "thickness", "ulcer"],
    )

def motor():
    """Data from a Simulated Motorcycle Accident"""
    return _read_numeric(
        "motor",
        ["times", "accel", "strata", "v"],
    )

def neuro():
    """Neurophysiological Point Process Data"""
    return _read_matrix("neuro", 6)

def nitrofen():
    """Toxicity of Nitrofen in Aquatic Systems"""
    return _read_numeric(
        "nitrofen",
        ["conc", "brood1", "brood2", "brood3", "total"],
    )

def nodal():
    """Nodal Involvement in Prostate Cancer"""
    return _read_numeric(
        "nodal",
        ["m", "r", "aged", "stage", "grade", "xray", "acid"],
    )

def nuclear():
    """Nuclear Power Station Construction Data"""
    return _read_numeric(
        "nuclear",
        ["cost", "date", "t1", "t2", "cap", "pr", "ne", "ct", "bw", "cum.n", "pt"],
    )

def paulsen():
    """Neurotransmission in Guinea Pig Brains"""
    return _read_numeric(
        "paulsen",
        ["y"],
    )

def poisons():
    """Animal Survival Times"""
    return _read_mixed(
        "poisons",
        ["time", "poison", "treat"],
        ["float", "str", "str"],
    )

def polar():
    """Pole Positions of New Caledonian Laterites"""
    return _read_numeric(
        "polar",
        ["lat", "long"],
    )

def remission():
    """Cancer Remission and Cell Activity"""
    columns = ["LI", "m", "r"]
    rows = np.array(
        [
            [0.4, 1.0, 0.0],
            [0.4, 1.0, 0.0],
            [0.5, 1.0, 0.0],
            [0.5, 1.0, 0.0],
            [0.6, 1.0, 0.0],
            [0.6, 1.0, 0.0],
            [0.6, 1.0, 0.0],
            [0.7, 1.0, 0.0],
            [0.7, 1.0, 0.0],
            [0.7, 1.0, 0.0],
            [0.8, 1.0, 0.0],
            [0.8, 1.0, 0.0],
            [0.8, 1.0, 0.0],
            [0.9, 1.0, 1.0],
            [1.0, 1.0, 0.0],
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
            [1.1, 1.0, 0.0],
            [1.1, 1.0, 1.0],
            [1.2, 1.0, 0.0],
            [1.3, 1.0, 1.0],
            [1.4, 1.0, 1.0],
            [1.6, 1.0, 0.0],
            [1.7, 1.0, 1.0],
            [1.9, 1.0, 0.0],
            [1.9, 1.0, 1.0],
            [1.9, 1.0, 1.0],
        ]
    )
    return columns, rows

def salinity():
    """Water Salinity and River Discharge"""
    columns = ["sal", "lag", "trend", "dis"]
    rows = np.array(
        [
            [7.6, 8.2, 4.0, 23.01],
            [7.7, 7.6, 5.0, 22.87],
            [4.3, 4.6, 0.0, 26.42],
            [5.9, 4.3, 1.0, 24.87],
            [5.0, 5.9, 2.0, 29.9],
            [6.5, 5.0, 3.0, 24.2],
            [8.3, 6.5, 4.0, 23.22],
            [8.2, 8.3, 5.0, 22.86],
            [13.2, 10.1, 0.0, 22.27],
            [12.6, 13.2, 1.0, 23.83],
            [10.4, 12.6, 2.0, 25.14],
            [10.8, 10.4, 3.0, 22.43],
            [13.1, 10.8, 4.0, 21.79],
            [12.3, 13.1, 5.0, 22.38],
            [10.4, 13.3, 0.0, 23.93],
            [10.5, 10.4, 1.0, 33.44],
            [7.7, 10.5, 2.0, 24.86],
            [9.5, 7.7, 3.0, 22.69],
            [12.0, 10.0, 0.0, 21.79],
            [12.6, 12.0, 1.0, 22.04],
            [13.6, 12.1, 4.0, 21.03],
            [14.1, 13.6, 5.0, 21.01],
            [13.5, 15.0, 0.0, 25.87],
            [11.5, 13.5, 1.0, 26.29],
            [12.0, 11.5, 2.0, 22.93],
            [13.0, 12.0, 3.0, 21.31],
            [14.1, 13.0, 4.0, 20.77],
            [15.1, 14.1, 5.0, 21.39],
        ]
    )
    return columns, rows

def survival():
    """Survival of Rats after Radiation Doses"""
    columns = ["dose", "surv"]
    rows = np.array(
        [
            [117.5, 44.0],
            [117.5, 55.0],
            [235.0, 16.0],
            [235.0, 13.0],
            [470.0, 4.0],
            [470.0, 1.96],
            [470.0, 6.12],
            [705.0, 0.5],
            [705.0, 0.32],
            [940.0, 0.11],
            [940.0, 0.015],
            [940.0, 0.019],
            [1410.0, 0.7],
            [1410.0, 0.006],
        ]
    )
    return columns, rows

def tau():
    """Tau Particle Decay Modes"""
    return _read_mixed(
        "tau",
        ["rate", "decay"],
        ["float", "str"],
    )

def tuna():
    """Tuna Sighting Data"""
    return _read_numeric(
        "tuna",
        ["y"],
    )

def urine():
    """Urine Analysis Data"""
    return _read_numeric(
        "urine",
        ["r", "gravity", "ph", "osmo", "cond", "urea", "calc"],
    )

def wool():
    """Australian Relative Wool Prices"""
    return _read_series("wool")

__all__ = [
    "acme",
    "aids",
    "aircondit",
    "aircondit7",
    "amis",
    "aml",
    "beaver",
    "bigcity",
    "brambles",
    "breslow",
    "calcium",
    "cane",
    "capability",
    "catsM",
    "cav",
    "cd4",
    "cd4_nested",
    "channing",
    "city",
    "claridge",
    "cloth",
    "co_transfer",
    "coal",
    "darwin",
    "dogs",
    "downs_bc",
    "ducks",
    "fir",
    "frets",
    "grav",
    "gravity",
    "hirose",
    "islay",
    "manaus",
    "melanoma",
    "motor",
    "neuro",
    "nitrofen",
    "nodal",
    "nuclear",
    "paulsen",
    "poisons",
    "polar",
    "remission",
    "salinity",
    "survival",
    "tau",
    "tuna",
    "urine",
    "wool",
]
