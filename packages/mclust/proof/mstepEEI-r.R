suppressPackageStartupMessages(library(mclust))
# Deterministic inputs shared with mstepEEI-py.py.
i <- 0:19
x <- outer(i, 0:2, function(a, b) ((7 * a + 13 * b) %% 17) / 4 - 2)
z <- cbind((3 * i + 0) %% 7 + 1, (3 * i + 5) %% 7 + 1, (3 * i + 10) %% 7 + 1) / 8
myPrior <- function(data, G, modelName, ...)
  list(shrinkage = 0.5, mean = if (is.matrix(data)) colMeans(data) else mean(data),
       scale = 2, dof = NCOL(data) + 3)
prior <- list(functionName = myPrior)
vals <- function(f) c(f$parameters$pro, as.vector(f$parameters$mean),
                      f$parameters$variance$scale, as.vector(f$parameters$variance$shape),
                      as.vector(f$parameters$variance$sigma), attr(f, "returnCode"))
# Untimed calls first, which also give the values.
value <- c(vals(mstepEEI(x, z)), vals(mstepEEI(x, z, prior = prior)))
elapsed <- numeric(20)
for (r in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  mstepEEI(x, z)
  elapsed[r] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
