.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3-66")
one <- function() {
  y <- c(7, 5, 4, 2, 11, 0, 3, 9, 6, 1, 8, 4, 2, 5, 0)
  mu <- c(
    5.2, 4.8, 4.1, 2.5, 9.0, 0.6, 3.2, 8.1, 5.9, 1.2,
    7.4, 3.9, 2.8, 4.6, 0.4
  )
  w <- c(1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1)
  th <- theta.ml(y, mu, weights = w)
  c(as.numeric(th), attr(th, "SE"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
for (item in value) cat(sprintf("%.17g\n", item))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
