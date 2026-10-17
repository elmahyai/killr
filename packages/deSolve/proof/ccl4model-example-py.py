import sys

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.ccl4model import ccl4model

Pm = {
    "BW": 0.182,
    "QP": 4.0,
    "QC": 4.0,
    "VFC": 0.08,
    "VLC": 0.04,
    "VMC": 0.74,
    "QFC": 0.05,
    "QLC": 0.15,
    "QMC": 0.32,
    "PLA": 16.17,
    "PFA": 281.48,
    "PMA": 13.3,
    "PTA": 16.17,
    "PB": 5.487,
    "MW": 153.8,
    "VMAX": 0.04321671,
    "KM": 0.4027255,
    "CONC": 1000.0,
    "KL": 0.02,
    "RATS": 1.0,
    "VCHC": 3.8,
}
y = {"AI": 21.0, "AAM": 0.0, "AT": 0.0, "AF": 0.0, "AL": 0.0, "CLT": 0.0, "AM": 0.0}
times = [0.0, 0.1, 0.2, 0.3]
out = ccl4model(times, y, Pm, method="rk4")
for row in out.data:
    print(f"{row[0]:8.4f} {row[-1]:12.4f}")
