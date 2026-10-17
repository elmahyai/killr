import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/vars")

from urca.display import show_text, summary
from urca.johansen import ca_jo
from urca.tests import ur_df, ur_kpss
from vars import Canada

x = [
    -0.62645381074233242,
    -0.44281048652025018,
    -1.2784390989302974,
    0.31684170320749422,
    0.64634947502285467,
    -0.17411890909516053,
    0.31331014333332474,
    1.051634848462542,
    1.6274162001160344,
    1.3220278129596783,
    2.8338089814105265,
    3.2236522178219573,
    2.6024116372801536,
    0.3877117501026538,
    1.5126426682457619,
    1.4677090592305311,
    1.451518796131585,
    2.3953550068168843,
    3.2165762019149726,
    3.8104775231324814,
    4.7294548947406998,
    5.5115911954717669,
    5.5861561788369576,
    3.5968044829735848,
    4.2166302308682955,
    4.1605014913392946,
    4.004705984633965,
    2.5339536007346903,
    2.0558035456260702,
    2.4737451058257727,
    3.8324246573548164,
    3.7296369300118211,
    4.1173085415711901,
    4.0635035009882854,
    2.6864439441596786,
    2.2714493808599987,
    1.8771594271496495,
    1.8178460304384638,
    2.9178714024223469,
    3.6810471508798912,
]


def normalize(text: str) -> str:
    import re

    out = []
    prev_blank = False
    for line in text.splitlines():
        line = line.rstrip()
        line = re.sub(r" +", " ", line) if line else line
        blank = line == ""
        if blank and prev_blank:
            continue
        out.append(line)
        prev_blank = blank
    return "\n".join(out)


def one():
    df = ur_df(x, type="drift", lags=1)
    kp = ur_kpss(x, type="mu", lags="short")
    jo = ca_jo(Canada(), type="trace", ecdet="const", K=2, spec="longrun")
    parts = [
        show_text(df),
        show_text(kp),
        show_text(jo),
        show_text(summary(df)),
    ]
    return normalize("\n".join(parts))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
