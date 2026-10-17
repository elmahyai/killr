import sys
sys.path.insert(0, "packages/mclust")
from mclust.bootstrap_family import print_summary_MclustBootstrap

x = {"modelName": "EEE", "G": 2, "nboot": 2, "type": "bs", "d": 1,
     "what": "ave", "pro": [.5, .5], "mean": [1.5, 3.5],
     "variance": [1.5, 3.5]}
print(print_summary_MclustBootstrap(x))
