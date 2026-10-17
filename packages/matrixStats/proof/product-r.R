set.seed(1)
x <- runif(100000, 0.5, 1.5)
writeBin(x, "/tmp/killr-product-sample.bin")

one <- function() matrixStats::product(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(median(elapsed) * 1000, "\n", sep = "")
cat(sprintf("%.17g\n", one()))
