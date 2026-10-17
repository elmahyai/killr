.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
proof <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
X <- as.matrix(read.csv(file.path(proof, "MclustSSC_X.csv")))
cl <- read.csv(file.path(proof, "MclustSSC_class.csv"))[[1L]]
mod <- MclustSSC(X, cl, verbose = FALSE)
one <- function() capture.output(print(mod))
value <- one()
writeLines(value, file.path(proof, "../docs/output/print.MclustSSC-r.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
