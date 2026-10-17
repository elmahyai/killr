.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
X <- matrix(c(0.1, 1.2, -0.4, 2.9, 3.3, 2.2, 0.7, 4.1, 1.5, 3.8, -1.0, 2.0, 0.3, 2.7, 1.9, 3.1), nrow = 8)
MU <- matrix(c(0.5, 0.2, 3.0, 2.5), nrow = 2)
pars <- list(pro = c(0.4, 0.6), mean = MU, variance = list(modelName = "EII", sigmasq = 1.1))
pars_noise <- list(pro = c(0.3, 0.5, 0.2), mean = MU, variance = list(modelName = "EII", sigmasq = 1.1))
emit <- function(res) c(res$loglik, attr(res, "returnCode"), as.vector(res$z))
one <- function() list(mclust:::estepEII(X, pars), mclust:::estepEII(X, pars_noise))
value <- one()
cat(sprintf("%.17g\n", c(emit(value[[1]]), emit(value[[2]]))), sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
