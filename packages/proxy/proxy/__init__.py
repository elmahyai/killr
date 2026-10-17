"""Python translation of the R package proxy."""

from proxy.dist import (
    as_dist,
    as_matrix,
    as_simil,
    col_dist,
    colMeans_dist,
    colSums_dist,
    dist,
    pr_DB,
    pr_dist2simil,
    pr_simil2dist,
    row_dist,
    rowMeans_dist,
    rowSums_dist,
    simil,
)

globals()["as.dist"] = as_dist
globals()["as.simil"] = as_simil
globals()["as.matrix"] = as_matrix
globals()["row.dist"] = row_dist
globals()["col.dist"] = col_dist
globals()["rowSums.dist"] = rowSums_dist
globals()["colSums.dist"] = colSums_dist
globals()["rowMeans.dist"] = rowMeans_dist
globals()["colMeans.dist"] = colMeans_dist

__all__ = [
    "dist",
    "simil",
    "as_dist",
    "as_simil",
    "as_matrix",
    "as.dist",
    "as.simil",
    "as.matrix",
    "pr_simil2dist",
    "pr_dist2simil",
    "row_dist",
    "col_dist",
    "rowSums_dist",
    "colSums_dist",
    "rowMeans_dist",
    "colMeans_dist",
    "row.dist",
    "col.dist",
    "rowSums.dist",
    "colSums.dist",
    "rowMeans.dist",
    "colMeans.dist",
    "pr_DB",
]
