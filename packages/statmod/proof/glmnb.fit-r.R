suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  X10 <- cbind(
    1,
    1:10,
    c(0.5, 1.1, -0.2, 0.8, 1.4, -0.5, 0.3, 1.2, -0.1, 0.9)
  )
  y10 <- c(3, 5, 2, 7, 4, 1, 6, 2, 8, 9)
  f1 <- glmnb.fit(X10, y10, dispersion = 0.2)
  X8 <- cbind(1, seq(0.2, 1.5, length.out = 8))
  y8 <- c(0, 2, 5, 1, 8, 3, 0, 4)
  w8 <- c(1, 1, 2, 1, 1, 0.5, 1, 1)
  off8 <- log(c(10, 12, 11, 9, 15, 13, 10, 14))
  f2 <- glmnb.fit(
    X8,
    y8,
    dispersion = rep(0.05, 8),
    weights = w8,
    offset = off8,
    start.method = "log(y)",
    tol = 1e-8
  )
  X6 <- cbind(1, 1:6)
  y6 <- c(2, 4, 6, 3, 8, 5)
  f3 <- glmnb.fit(X6, y6, dispersion = 0.1, coef.start = c(0.1, 0.05), maxit = 30)
  c(
    f1$coefficients,
    f1$fitted.values,
    f1$deviance,
    f1$iter,
    f2$coefficients,
    f2$fitted.values,
    f2$deviance,
    f2$iter,
    f3$coefficients,
    f3$fitted.values,
    f3$deviance,
    f3$iter
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
