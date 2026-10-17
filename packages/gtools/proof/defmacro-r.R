.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

one <- function() {
  mul <- defmacro(a, b, expr = a * b)
  i <- 2
  j <- 3
  k <- 4
  as.numeric(c(mul(2, 3 + 4), mul(i, j + k)))
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(format(value, digits = 17), collapse = ","), median(elapsed) * 1000))
