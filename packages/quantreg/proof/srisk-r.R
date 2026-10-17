suppressPackageStartupMessages(library(quantreg))
X <- matrix(c(0.02,0.01,-0.01, 0.03,0,0.02, -0.02,0.04,0.01, 0.01,-0.01,0.02), 4, 3, byrow=TRUE)
one <- function() {fit <- srisk(X, mu=0.01, lambda=1e6); c(fit$pihat, fit$muhat, fit$sigma)}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
