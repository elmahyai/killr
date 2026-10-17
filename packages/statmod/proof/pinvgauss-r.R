suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  qs <- c(0.2, 1, 2.5, 10, NA, -1, 0, Inf, NaN)
  mus <- c(1, 1.5, 2, 0.5, 1, 1, 0, Inf, 1)
  phis <- c(0.3, 0.7, 1, 2, 0.5, 1, 1, 1, 0)
  c(
    pinvgauss(qs, mean = mus, dispersion = phis),
    pinvgauss(qs, mean = mus, dispersion = phis, log.p = TRUE),
    pinvgauss(1.2, mean = 2, shape = 4),
    pinvgauss(c(0.5, 1.5), mean = 1, dispersion = c(0.2, 0.8)),
    pinvgauss(c(0.5, 1.5), mean = 1, dispersion = c(0.2, 0.8), lower.tail = FALSE),
    pinvgauss(2e6, mean = 1, dispersion = 0.001, lower.tail = FALSE),
    pinvgauss(0.5, mean = 1, dispersion = 1e-15),
    as.numeric(pinvgauss(matrix(c(0.8, 1.2), nrow = 2), mean = 1, dispersion = 0.5))
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
