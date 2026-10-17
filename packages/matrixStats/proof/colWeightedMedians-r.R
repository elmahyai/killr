set.seed(1)
x <- matrix(rnorm(100 * 40), nrow = 100, ncol = 40)
w <- runif(100)
writeBin(as.numeric(x), "/tmp/colWeightedMedians-x.bin")
writeBin(as.numeric(w), "/tmp/colWeightedMedians-w.bin")
one <- function() matrixStats::colWeightedMedians(x, w = w, na.rm = FALSE)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
writeBin(as.numeric(one()), "/tmp/colWeightedMedians-r.bin")
