# R reference for hgridcent(). Run from the repository root:
#   Rscript packages/hexbin/proof/hgridcent_r.R
source("packages/hexbin/proof/_proof_common.R")

record_grid <- function(prefix, g) {
  put_num(paste0(prefix, ".x"), g$x)
  put_num(paste0(prefix, ".y"), g$y)
  put_num(paste0(prefix, ".dimen"), g$dimen)
  put_num(paste0(prefix, ".dx"), g$dx)
  put_num(paste0(prefix, ".dy"), g$dy)
}

record_grid("case1", hgridcent(30, c(-5, 5), c(-3, 3), 1))
record_grid("case2", hgridcent(12, c(-5, 5), c(-3, 3), 0.8, edge.add = 2))
record_grid("case3", hgridcent(20, c(-5, 5), c(-3, 3), 1.2, edge.add = 1))
record_grid("case4", hgridcent(7.5, c(0, 9), c(0, 4), 1))

record_timing(function() hgridcent(300, c(-5, 5), c(-3, 3), 1, edge.add = 2))
write_ref("hgridcent")
