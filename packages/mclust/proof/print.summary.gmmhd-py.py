import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.gmmhd_family import print_summary_gmmhd

obj = {
    "title": "GMM with high-density connected components for clustering",
    "Mclust": {"G": 2, "modelName": "VVV"},
    "MclustDR": {"G": 2, "modelName": "EEE"},
    "clusterCores": {"values": [2, 1], "names": [1, 2]},
    "cluster": {"values": [2, 2], "names": [1, 2]},
}
print_summary_gmmhd(obj)
