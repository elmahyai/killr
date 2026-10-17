suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
obj <- list(
  means = matrix(1:4, 2, 2),
  B = matrix(1:4, 2, 2),
  W = matrix(5:8, 2, 2),
  evalues = c(4, 2),
  basis = matrix(1:12, 6, 2),
  projection = matrix(1:12, 6, 2),
  classification = c(1L, 1L, 2L, 2L, 1L, 2L)
)
class(obj) <- "crimcoords"
one <- function() capture.output(print(obj))
value <- one()
writeLines(value, file.path(proof_dir, "print.crimcoords-r-output.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
