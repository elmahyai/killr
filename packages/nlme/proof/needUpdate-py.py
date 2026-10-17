import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corar1 import corAR1
from nlme.needupdate import Attributed, needUpdate
from nlme.nlmestruct import nlmeStruct
from nlme.restruct import load_pixel_csv, reStruct
from nlme.var_ident import varIdent
from nlme.varcomb import varComb


def one():
    pixel = load_pixel_csv()
    rs = reStruct({"Dog": "~day", "Side": "~1"}, data=pixel)
    return [
        float(needUpdate(corAR1(0.3, form="~1 | Dog"))),
        float(needUpdate(rs)),
        float(needUpdate(varIdent(form="~1"))),
        float(needUpdate(varComb(varIdent(form="~1"), varIdent(form="~1")))),
        float(needUpdate(nlmeStruct(reStruct=Attributed(1.0, {"needUpdate": True})))),
        float(needUpdate(nlmeStruct(reStruct=Attributed(1.0, {"needUpdate": False}),
                                    corStruct=corAR1(0.3)))),
        float(needUpdate(Attributed(2.0, {"needUpdate": True}))),
        float(needUpdate(Attributed(2.0, {"needUpdate": False}))),
        float(needUpdate(Attributed(2.0, {}))),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
