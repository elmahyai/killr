suppressPackageStartupMessages({library(quantreg); library(SparseM)})
x <- 2 * sin(1:40)
y <- -0.4 * x + sin(x) + 0.3 * cos(5 * (1:40))
d <- data.frame(y = y, x = x)
one <- function() {
  out <- c()
  for (cons in c("I", "C")) {
    q <- qss(x, constraint = cons, lambda = 2)
    out <- c(out, q$x$x, as.vector(t(as.matrix(q$F))), as.vector(t(as.matrix(q$A))),
             as.vector(t(as.matrix(q$R))), q$r, q$lambda)
    f <- rqss(y ~ qss(x, constraint = cons, lambda = 2), tau = 0.5, data = d)
    out <- c(out, as.vector(t(f$qss[[1]]$xyz)), f$coef, f$fidelity)
  }
  out
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
