"""Python translation of the R package slam."""

import numpy as np

from slam._arrays import (
    abind_simple_sparse_array,
    as_array,
    as_matrix,
    as_simple_sparse_array,
    as_simple_triplet_matrix,
    col_means,
    col_norms,
    col_sums,
    colapply_simple_triplet_matrix,
    crossapply_simple_triplet_matrix,
    crossprod_simple_triplet_matrix,
    drop_simple_sparse_array,
    extend_simple_sparse_array,
    is_simple_sparse_array,
    is_simple_triplet_matrix,
    matprod_simple_triplet_matrix,
    reduce_simple_sparse_array,
    rollup,
    row_means,
    row_norms,
    row_sums,
    rowapply_simple_triplet_matrix,
    simple_sparse_array,
    simple_triplet_diag_matrix,
    simple_triplet_matrix,
    simple_triplet_zero_matrix,
    simplify_simple_sparse_array,
    tcrossapply_simple_triplet_matrix,
    tcrossprod_simple_triplet_matrix,
)
from slam.foreign import read_stm_CLUTO, read_stm_MC, write_stm_CLUTO, write_stm_MC
from slam.options import slam_options


def simple_sparse_zero_array(dim):
    dim = np.asarray(dim, dtype=int).reshape(-1)
    return simple_sparse_array(np.zeros((0, dim.size), dtype=int), [], dim)


__all__ = [
    "abind_simple_sparse_array",
    "as_simple_sparse_array",
    "as_simple_triplet_matrix",
    "col_means",
    "col_norms",
    "col_sums",
    "colapply_simple_triplet_matrix",
    "crossapply_simple_triplet_matrix",
    "crossprod_simple_triplet_matrix",
    "drop_simple_sparse_array",
    "extend_simple_sparse_array",
    "is_simple_sparse_array",
    "is_simple_triplet_matrix",
    "matprod_simple_triplet_matrix",
    "read_stm_CLUTO",
    "read_stm_MC",
    "reduce_simple_sparse_array",
    "rollup",
    "row_means",
    "row_norms",
    "row_sums",
    "rowapply_simple_triplet_matrix",
    "simple_sparse_array",
    "simple_sparse_zero_array",
    "simple_triplet_diag_matrix",
    "simple_triplet_matrix",
    "simple_triplet_zero_matrix",
    "simplify_simple_sparse_array",
    "slam_options",
    "tcrossapply_simple_triplet_matrix",
    "tcrossprod_simple_triplet_matrix",
    "write_stm_CLUTO",
    "write_stm_MC",
]
