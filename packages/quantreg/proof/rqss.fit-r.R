suppressPackageStartupMessages({library(quantreg); library(SparseM)})
n <- 60
i <- 1:n
x <- 2 * sin(i)
z <- cos(0.7 * i)
y <- sin(x) + 0.5 * z + 0.3 * sin(7 * i)
X <- as.matrix.csr(cbind(1, x, z))
one <- function() {
  f <- rqss.fit(X, y, tau = 0.3)
  rho <- sum(f$resid * (0.3 - (f$resid < 0)))
  c(f$coef, rho)
}
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
