set.seed(1)
x <- matrix(rnorm(400 * 250), nrow = 400, ncol = 250)
writeBin(as.numeric(x), "means2-x.bin")
one <- function() matrixStats::colMeans2(x, na.rm = FALSE, refine = TRUE)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
