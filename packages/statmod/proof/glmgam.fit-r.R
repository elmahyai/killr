suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  y10 <- c(
    3.2, 5.1, 4.8, 6.3, 2.9, 7.4, 5.5, 4.1, 6.8, 3.7
  )
  X10 <- cbind(
    1,
    c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    c(0.5, 1.1, -0.2, 0.8, 1.4, -0.5, 0.3, 1.2, -0.1, 0.9)
  )
  y6 <- c(1.2, 0.8, 2.5, 3.1, 0.4, 1.9)
  X6 <- cbind(1, c(2, -1, 3, 0.5, -2, 1.5), c(-0.3, 1.1, 0.7, -0.8, 0.2, 1.3))
  start <- c(0.5, 0.05, 0.1)
  f1 <- glmgam.fit(X10, y10)
  f2 <- glmgam.fit(X6, y6, coef.start = start, tol = 1e-8, maxit = 80)
  c(
    f1$coefficients,
    f1$fitted.values,
    f1$deviance,
    f1$iter,
    f2$coefficients,
    f2$fitted.values,
    f2$deviance,
    f2$iter
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
