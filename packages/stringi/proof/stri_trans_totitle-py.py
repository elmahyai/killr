import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA

from stringi.trans import stri_trans_totitle

def show(item):
    if item is NA:
        return None
    if isinstance(item, list):
        return [show(part) for part in item]
    if isinstance(item, dict):
        return {key: show(value) for key, value in item.items()}
    return item



def one():
    sentence = "stringi is a FREE R pAcKaGe. WItH NO StrinGS attached."
    return {
        "word": stri_trans_totitle([sentence]),
        "sentence": stri_trans_totitle([sentence], type="sentence"),
        "one": stri_trans_totitle(["one. two. three."], type="sentence"),
        "two": stri_trans_totitle(["one. Two. three."], type="sent"),
        "tr": stri_trans_totitle(["iPhone ISTANBUL"], locale="tr_TR"),
        "na": stri_trans_totitle([NA, "NA", ""]),
    }

warnings.filterwarnings("ignore", category=UserWarning)
value = show(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_trans_totitle-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('stri_trans_totitle of the stringi sentence returns Stringi Is A Free R Package. With No Strings Attached.' + "\n", encoding="utf-8")
