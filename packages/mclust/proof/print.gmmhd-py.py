import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.gmmhd_family import print_gmmhd

obj = {
    "Mclust": {"G": 2, "modelName": "VVV"},
    "MclustDR": {"G": 2, "modelName": "EEE"},
    "numClusters": 2,
}
print_gmmhd(obj)
