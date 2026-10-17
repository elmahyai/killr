import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.cumulant_digamma import cumulant_digamma

theta = np.array([-1, -0.5, -0.1], dtype=float)
print(cumulant_digamma(theta))
