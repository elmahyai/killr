
import json
import statistics
import tempfile
import time
import warnings
from datetime import date, datetime, timezone
from pathlib import Path

warnings.simplefilter("ignore")
from readr import *
from readr.parse import Factor, Hms
from readr.read import Table

def cell(value):
    if isinstance(value, Hms):
        return format(value.seconds, ".17g")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if value != value:
            return "NaN"
        if value == float("inf"):
            return "Inf"
        if value == float("-inf"):
            return "-Inf"
        return format(value, ".17g")
    if isinstance(value, int):
        return str(value)
    if value is None:
        return "NA"
    return str(value)

def flatv(values):
    if isinstance(values, Factor):
        values = values.values
    if isinstance(values, (str, bytes)) or values is None:
        return cell(values)
    return ",".join(cell(value) for value in values)

def flatdf(frame):
    bits = "|".join(frame.names)
    for column in frame.columns:
        bits += ";" + flatv(column)
    return bits

def yn(value):
    return "TRUE" if bool(value) else "FALSE"

def frame(names, columns):
    return Table(list(names), [list(column) for column in columns], len(columns[0]) if columns else 0)

def one():
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    day_ab = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    names = date_names(months, short, days, day_ab)
    return names.mon[0] + ";" + names.mon_ab[0] + ";" + names.day[0] + ";" + names.day_ab[0]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
