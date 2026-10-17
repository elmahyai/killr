.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  data <- array(c(10, 20, 30, 40), dim = c(2, 2), dimnames = list(A = c("a1", "a2"), B = c("b1", "b2")))
  fm <- loglm(~ A + B, data)
  c(fm$lrt, fm$pearson, fm$df, fm$nobs)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
