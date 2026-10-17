.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nortest))
x <- c(2.1, 3.4, NA, 1.2, 5.6, 4.0, 3.3, 2.8, 6.1, 1.9, NaN, 4.4)
one <- function() pearson.test(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
