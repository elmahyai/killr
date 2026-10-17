import statistics
import sys
import time
import types

import numpy as np

_mass_root = "/home/ahmed/killr_projects/killr/packages/MASS/mass"
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
if "mass" not in sys.modules:
    _pkg = types.ModuleType("mass")
    _pkg.__path__ = [_mass_root]
    sys.modules["mass"] = _pkg

from mass.theta_md import theta_md
from mass.theta_ml import theta_ml


def one():
    y = np.array(
        [5, 0, 6, 6, 3, 1, 0, 2, 5, 1, 0, 6, 1, 1, 3, 0, 3, 0, 0, 5, 1, 2, 4, 2, 4],
        dtype=float,
    )
    mu = np.array(
        [
            3.4822229462263152,
            1.5937504569526852,
            2.3180551009962223,
            2.5847841056136609,
            2.3568830848608955,
            1.9179429354901891,
            3.6855793106658874,
            1.9268427121392488,
            4.5226805873876845,
            1.9518575599632846,
            3.3905274056106354,
            5.0400077249380599,
            1.1426030825870765,
            1.7887816148026197,
            1.8969961697746012,
            2.5880088019714798,
            1.7848393400723972,
            0.68487340937627095,
            0.74728452989866612,
            3.4114608288535142,
            1.7687790428718941,
            0.97515995152607471,
            1.8676619282108053,
            3.269269289217442,
            4.3031480800396755,
        ],
        dtype=float,
    )
    dfr = 23.0
    w = np.array(
        [
            3.48222368170982,
            1.5937535568781458,
            2.3180576832203075,
            2.584786360451433,
            2.3568856234854132,
            1.917945878168787,
            3.6855796250569437,
            1.926845648683885,
            4.522678919661935,
            1.9518604787800111,
            3.390528322439978,
            5.0400046555583948,
            1.1426061485164767,
            1.7887846359667774,
            1.8969991265279447,
            2.588011052464271,
            1.7848423633140538,
            0.68487602471539943,
            0.74728723899159732,
            3.4114617047622264,
            1.7687820743769087,
            0.97516291095653018,
            1.8676649038109703,
            3.2692704373847694,
            4.3031469682550574,
        ],
        dtype=float,
    )
    th = theta_md(y, mu, dfr)
    ml = theta_ml(y, mu, weights=w)
    return np.array([float(th), ml.SE], dtype=float)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
