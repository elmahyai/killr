.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rootSolve))

g2 <- function(t, y, p) {
  Y <- matrix(y, nrow = 3, ncol = 3)
  dY <- Y
  for (i in 1:3) for (j in 1:3) {
    left <- if (i == 1) 0 else Y[i - 1, j]
    right <- if (i == 3) 1 else Y[i + 1, j]
    down <- if (j == 1) 0 else Y[i, j - 1]
    up <- if (j == 3) 0 else Y[i, j + 1]
    dY[i, j] <- left + right + down + up - 4 * Y[i, j]
  }
  list(as.vector(dY))
}
one <- function() {
steady.2D(y = rep(0.2, 9), func = g2, dimens = c(3, 3), nspec = 1)$y
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
