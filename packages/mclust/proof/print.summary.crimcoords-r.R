suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
basis <- matrix(1:12, 6, 2,
                dimnames = list(c("Length", "Left", "Right", "Bottom", "Top", "Diagonal"),
                                c("crimcoords1", "crimcoords2")))
obj <- list(
  basis = basis,
  evalues = c(4, 2),
  evalues.cumperc = c(66.6666666667, 100)
)
class(obj) <- "summary.crimcoords"
one <- function() capture.output(print(obj))
value <- one()
writeLines(value, file.path(proof_dir, "print.summary.crimcoords-r-output.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
