suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  xs <- c(0.2, 1, 2.5, 10, NA, -1, 0, Inf, NaN)
  mus <- c(1, 1.5, 2, 0.5, 1, 1, 0, Inf, 1)
  phis <- c(0.3, 0.7, 1, 2, 0.5, 1, 1, 1, 0)
  c(
    dinvgauss(xs, mean = mus, dispersion = phis),
    dinvgauss(xs, mean = mus, dispersion = phis, log = TRUE),
    dinvgauss(1.2, mean = 2, shape = 4),
    dinvgauss(c(0.5, 1.5), mean = 1, dispersion = c(0.2, 0.8)),
    as.numeric(dinvgauss(matrix(c(0.8, 1.2), nrow = 2), mean = 1, dispersion = 0.5))
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
