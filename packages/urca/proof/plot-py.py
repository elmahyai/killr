import json
import math
import statistics
import sys
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.display import plot
from urca.tests import ur_df

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


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    df = ur_df(x, type="drift", lags=1)
    result = plot(df)
    for figure in result.figures:
        plt.close(figure)
    return result.values.tolist()


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    result = plot(ur_df(x, type="drift", lags=1))
    for figure in result.figures:
        plt.close(figure)
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
