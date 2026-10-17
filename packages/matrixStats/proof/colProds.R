set.seed(1)
x <- matrix(runif(80 * 40, 0.5, 1.5), nrow = 80, ncol = 40)
writeBin(as.numeric(x), "/tmp/rowProds-seed1.bin")

time_one <- function(fun, path) {
  invisible(fun())
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    fun()
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  writeBin(as.numeric(fun()), path)
  median(elapsed) * 1000
}

cat(sprintf("%.17g\n", time_one(function() matrixStats::colProds(x), "/tmp/colProds-r.bin")))
cat(sprintf("%.17g\n", time_one(
  function() matrixStats::colProds(x, method = "expSumLog"),
  "/tmp/colProds-exp-r.bin"
)))
