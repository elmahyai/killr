import json
import math
import statistics
import sys
import time
import warnings

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/moments")
warnings.simplefilter("ignore")

from moments import *


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    result = jarque_test([-0.6264538107423324, 0.18364332422208224, -0.8356286124100472, 1.5952808021377916, 0.3295077718153605, -0.8204683841180153, 0.4874290524284853, 0.7383247051292173, 0.5757813516534923, -0.305388387156356, 1.511781168450848, 0.3898432364114311, -0.6212405805418038, -2.2146998871775, 1.1249309181431082, -0.04493360901523085, -0.016190263098946087, 0.9438362106852992, 0.8212211950980886, 0.5939013212175088, 0.9189773716082182, 0.7821363007310671, 0.0745649833651906, -1.9893516958633728, 0.6198257478947102, -0.056128739529000785, -0.1557955067053293, -1.4707523838992744, -0.47815005510862035, 0.4179415601997024])
    return list(result.statistic.values()) + [result.p_value]


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
