
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
def one():
    return flat(DonchianChannel(hl))
value = one()

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value if isinstance(value, list) else [value]
print(json.dumps({"value": shown, "median_ms": statistics.median(elapsed)}))
