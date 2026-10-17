suppressPackageStartupMessages(library(quantreg))
n <- 60
i <- 1:n
x <- 2 * sin(i)
z <- cos(0.7 * i)
y <- -0.4 * x + sin(x) + 0.5 * z + 0.3 * sin(7 * i)
d <- data.frame(y = y, x = x, z = z)
objective <- function(f) f$fidelity + sum(abs(f$resid[(f$n + 1):length(f$resid)]))
one <- function() {
  f1 <- rqss(y ~ qss(x, constraint = "I", lambda = 2) + z, tau = 0.5, data = d)
  f2 <- rqss(y ~ qss(x, constraint = "C", lambda = 2) + z, tau = 0.5, data = d)
  c(f1$coef, objective(f1), f2$coef, objective(f2))
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
