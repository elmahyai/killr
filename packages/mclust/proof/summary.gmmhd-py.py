import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.gmmhd_family import summary_gmmhd

obj = {
    "Mclust": {"G": 2, "modelName": "VVV"},
    "MclustDR": {"G": 2, "modelName": "EEE"},
    "clusterCores": np.array([1, 1, 2, np.nan]),
    "cluster": np.array([1, 1, 2, 2]),
}
print(summary_gmmhd(obj))
