.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rootSolve))
approach <- function(t, y, p) list(1 - y)
out <- steady.3D(y = rep(0, 8), func = approach, dimens = c(2, 2, 2))
one <- function() {
pdf(NULL)
image(out)
dev.off()
out$y
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
