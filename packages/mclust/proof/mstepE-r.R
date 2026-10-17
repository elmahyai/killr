suppressPackageStartupMessages(library(mclust))
# Deterministic inputs shared with mstepE-py.py.
k <- 0:19
x <- ((7 * k) %% 17) / 4 - 2
z <- cbind((3 * k + 0) %% 7 + 1, (3 * k + 5) %% 7 + 1, (3 * k + 10) %% 7 + 1) / 8
myPrior <- function(data, G, modelName, ...)
  list(shrinkage = 0.5, mean = if (is.matrix(data)) colMeans(data) else mean(data),
       scale = 2, dof = NCOL(data) + 3)
prior <- list(functionName = myPrior)
vals <- function(f) c(f$parameters$pro, f$parameters$mean, f$parameters$variance$sigmasq, attr(f, "returnCode"))
# Untimed calls first, which also give the values.
value <- c(vals(mstepE(x, z)), vals(mstepE(x, z, prior = prior)))
elapsed <- numeric(20)
for (r in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  mstepE(x, z)
  elapsed[r] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
