"""Python translation of the R package class.

The package name is a Python keyword, so callers load it with
importlib.import_module("class").
"""

import importlib

_knn = importlib.import_module("class.knn")
_lvq = importlib.import_module("class.lvq")
_som = importlib.import_module("class.som")
_edit = importlib.import_module("class.edit")

knn = _knn.knn
knn1 = _knn.knn1
knn_cv = _knn.knn_cv
lvqinit = _lvq.lvqinit
lvq1 = _lvq.lvq1
lvq2 = _lvq.lvq2
lvq3 = _lvq.lvq3
olvq1 = _lvq.olvq1
lvqtest = _lvq.lvqtest
somgrid = _som.somgrid
batchSOM = _som.batchSOM
SOM = _som.SOM
multiedit = _edit.multiedit
condense = _edit.condense
reduce_nn = _edit.reduce_nn

__all__ = [
    "SOM",
    "batchSOM",
    "condense",
    "knn",
    "knn1",
    "knn_cv",
    "lvq1",
    "lvq2",
    "lvq3",
    "lvqinit",
    "lvqtest",
    "multiedit",
    "olvq1",
    "reduce_nn",
    "somgrid",
]
