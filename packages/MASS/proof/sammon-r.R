.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  pts <- matrix(
    c(
      0, 3, 1, 4, 2, 5,
      1, 1, 2, 2, 0, 3,
      0.5, 1.5, 0.2, 1.1, 0.8, 1.2
    ),
    6,
    3
  )
  d <- as.matrix(dist(pts))
  y0 <- matrix(
    c(
      -1.2, 0.3, 0.9, -0.4, 1.1, -0.7,
      0.5, -0.8, 0.2, 1.0, -0.3, 0.6
    ),
    6,
    2
  )
  fit <- sammon(d, y = y0, k = 2, niter = 100, trace = FALSE)
  c(as.vector(fit$points), fit$stress)
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
