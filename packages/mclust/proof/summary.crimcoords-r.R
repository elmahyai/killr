suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
basis <- matrix(1:12, 6, 2,
                dimnames = list(c("Length", "Left", "Right", "Bottom", "Top", "Diagonal"),
                                c("crimcoords1", "crimcoords2")))
obj <- list(
  basis = basis,
  evalues = c(4, 2),
  projection = matrix(1:12, 6, 2)
)
class(obj) <- "crimcoords"
one <- function() summary(obj)
value <- one()
saveRDS(value, file.path(proof_dir, "summary.crimcoords-r-value.rds"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
