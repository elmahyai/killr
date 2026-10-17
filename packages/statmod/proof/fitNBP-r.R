suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

collect <- function(fit) {
  c(fit$dispersion, fit$coefficients, fit$fitted.values)
}

one <- function() {
  y_small <- matrix(c(3, 5, 2, 7, 4, 1, 6, 2), 2, 4)
  y42 <- matrix(
    c(
      6, 6, 5, 5, 8, 5, 1, 7, 10, 4, 6, 7, 6, 3, 3, 7, 7, 1, 0, 0, 2, 1, 1, 0, 1, 2, 2, 3,
      0, 5, 0, 1, 3, 1, 5, 6, 1, 3, 0, 10
    ),
    10,
    4
  )
  y_one <- matrix(c(2, 5, 1, 4, 0, 3, 6, 2, 8), 3, 3)
  y_three <- matrix(c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12), 3, 4)
  c(
    collect(fitNBP(y_small, group = c(1, 1, 2, 2), lib.size = rep(100, 4))),
    collect(fitNBP(y42, group = c(1, 1, 2, 2), lib.size = rep(50000, 4))),
    collect(fitNBP(y_one, lib.size = c(20, 25, 30))),
    collect(fitNBP(y_three, group = c(1, 2, 3, 1), lib.size = rep(50, 4), maxit = 25L))
  )
}

value <- one()
elapsed <- numeric(0)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
