import sys
sys.path.insert(0, "packages/mclust")
from mclust.bootstrap_family import print_MclustBootstrap

x = {"G": 2, "modelName": "EEE", "nboot": 2, "type": "bs", "nonfit": 0,
     "pro": [[.4, .3], [.6, .7]], "mean": [[[1, 3]], [[2, 4]]],
     "variance": [[[[1, 3]]], [[[2, 4]]]],
     "parameters": {"pro": [], "mean": [], "variance": []}}
print(print_MclustBootstrap(x))
