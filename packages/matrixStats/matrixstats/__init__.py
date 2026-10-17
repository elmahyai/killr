"""Python translation of the R package matrixStats."""

from matrixstats.alloc import allocArray, allocMatrix, allocVector
from matrixstats.anymissing import anyMissing
from matrixstats.rowavgs import colAvgsPerRowSet, rowAvgsPerColSet
from matrixstats.rowalls import (
    allValue,
    anyValue,
    colAlls,
    colAnyMissings,
    colAnyNAs,
    colAnys,
    rowAlls,
    rowAnyMissings,
    rowAnyNAs,
    rowAnys,
)
from matrixstats.rowcounts import colCounts, count, rowCounts
from matrixstats.rowcollapse import colCollapse, rowCollapse
from matrixstats.bincounts import binCounts
from matrixstats.binmeans import binMeans
from matrixstats.diff2 import diff2
from matrixstats.vardiff import (
    colIQRDiffs,
    colMadDiffs,
    colSdDiffs,
    colVarDiffs,
    iqrDiff,
    madDiff,
    rowIQRDiffs,
    rowMadDiffs,
    rowSdDiffs,
    rowVarDiffs,
    sdDiff,
    varDiff,
)
from matrixstats.indexbyrow import indexByRow
from matrixstats.iqr import iqr
from matrixstats.rowiqrs import colIQRs, rowIQRs
from matrixstats.rowquantiles import colQuantiles, rowQuantiles
from matrixstats.logsumexp import logSumExp
from matrixstats.mean2 import mean2
from matrixstats.product import product
from matrixstats.sum2 import sum2
from matrixstats.weightedmean import weightedMean
from matrixstats.weightedmedian import weightedMedian
from matrixstats.weightedmad import colWeightedMads, rowWeightedMads, weightedMad
from matrixstats.weightedvar import (
    colWeightedSds,
    colWeightedVars,
    rowWeightedSds,
    rowWeightedVars,
    weightedSd,
    weightedVar,
)
from matrixstats.rowweightedmeans import colWeightedMeans, rowWeightedMeans
from matrixstats.rowweightedmedians import colWeightedMedians, rowWeightedMedians
from matrixstats.rowcummaxs import colCummaxs, rowCummaxs
from matrixstats.rowcummins import colCummins, rowCummins
from matrixstats.rowcumprods import colCumprods, rowCumprods
from matrixstats.rowcumsums import colCumsums, rowCumsums
from matrixstats.rowdiffs import colDiffs, rowDiffs
from matrixstats.rowlogsumexps import colLogSumExps, rowLogSumExps
from matrixstats.rowmads import colMads, rowMads
from matrixstats.rowmeans2 import colMeans2, rowMeans2
from matrixstats.rowmedians import colMedians, rowMedians
from matrixstats.roworderstats import colOrderStats, rowOrderStats
from matrixstats.rowprods import colProds, rowProds
from matrixstats.colranges import colMaxs, colMins, colRanges
from matrixstats.rowranges import rowMaxs, rowMins, rowRanges
from matrixstats.rowranks import colRanks, rowRanks
from matrixstats.rowsds import colSds, rowSds
from matrixstats.rowsums2 import colSums2, rowSums2
from matrixstats.rowtabulates import colTabulates, rowTabulates
from matrixstats.rowvars import colVars, rowVars
from matrixstats.signtabulate import signTabulate
from matrixstats.x_op_y import t_tx_OP_y, x_OP_y

__all__ = [
    "allocArray",
    "allocMatrix",
    "allocVector",
    "allValue",
    "anyMissing",
    "anyValue",
    "binCounts",
    "binMeans",
    "colAvgsPerRowSet",
    "colAlls",
    "colAnyMissings",
    "colAnyNAs",
    "colAnys",
    "colCollapse",
    "colCounts",
    "colCummaxs",
    "colCummins",
    "colCumprods",
    "colCumsums",
    "colDiffs",
    "colIQRDiffs",
    "colIQRs",
    "colLogSumExps",
    "colMads",
    "colMadDiffs",
    "colMaxs",
    "colMeans2",
    "colMedians",
    "colMins",
    "colOrderStats",
    "colProds",
    "colQuantiles",
    "colRanges",
    "colRanks",
    "colSds",
    "colSdDiffs",
    "colSums2",
    "colTabulates",
    "colVars",
    "colVarDiffs",
    "colWeightedMads",
    "colWeightedMeans",
    "colWeightedMedians",
    "colWeightedSds",
    "colWeightedVars",
    "count",
    "diff2",
    "indexByRow",
    "iqr",
    "iqrDiff",
    "logSumExp",
    "madDiff",
    "mean2",
    "product",
    "rowAvgsPerColSet",
    "rowAlls",
    "rowAnyMissings",
    "rowAnyNAs",
    "rowAnys",
    "rowCollapse",
    "rowCounts",
    "rowCummaxs",
    "rowCummins",
    "rowCumprods",
    "rowCumsums",
    "rowDiffs",
    "rowIQRDiffs",
    "rowIQRs",
    "rowLogSumExps",
    "rowMads",
    "rowMadDiffs",
    "rowMeans2",
    "rowMedians",
    "rowMaxs",
    "rowMins",
    "rowOrderStats",
    "rowProds",
    "rowQuantiles",
    "rowRanges",
    "rowRanks",
    "rowSds",
    "rowSdDiffs",
    "rowSums2",
    "rowTabulates",
    "rowVars",
    "rowVarDiffs",
    "rowWeightedMads",
    "rowWeightedMeans",
    "rowWeightedMedians",
    "rowWeightedSds",
    "rowWeightedVars",
    "sdDiff",
    "signTabulate",
    "sum2",
    "t_tx_OP_y",
    "varDiff",
    "weightedMad",
    "weightedMean",
    "weightedMedian",
    "weightedSd",
    "weightedVar",
    "x_OP_y",
]
