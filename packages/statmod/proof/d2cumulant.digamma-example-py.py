import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.d2cumulant_digamma import d2cumulant_digamma

theta = np.array([-1, -0.5, -0.1], dtype=float)
print(d2cumulant_digamma(theta))
