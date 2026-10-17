.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

x <- list(
  G = 1:3, modelName = "EEE",
  obs = c(12.3456789, 3.2, 0.000123),
  boot = matrix(seq(0.5, 15.25, by = 0.25), nrow = 20, ncol = 3)
)
h <- hist(x$boot[, 1], breaks = "Scott", plot = FALSE)
raw <- range(h$breaks, x$boot[, 1], x$obs[1], na.rm = TRUE)
xlim <- extendrange(raw, f = 0.05)
cat(sprintf("%.17g\n", c(h$breaks, h$density, x$obs[1], xlim)))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  h <- hist(x$boot[, 1], breaks = "Scott", plot = FALSE)
  raw <- range(h$breaks, x$boot[, 1], x$obs[1], na.rm = TRUE)
  extendrange(raw, f = 0.05)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
