suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  ps <- c(0.001, 0.05, 0.5, 0.95, 0.999, NA, -0.1, 0, 1, 1.1)
  mus <- c(1, 1.5, 2, 0.5, 1, 1, 1, 1, 1, 1)
  phis <- c(0.3, 0.7, 1, 2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
  ps_ok <- c(0.001, 0.05, 0.5, 0.95, 0.999)
  mus_ok <- c(1, 1.5, 2, 0.5, 1)
  phis_ok <- c(0.3, 0.7, 1, 2, 0.5)
  c(
    qinvgauss(ps, mean = mus, dispersion = phis),
    qinvgauss(log(ps_ok), mean = mus_ok, dispersion = phis_ok, log.p = TRUE),
    qinvgauss(0.6, mean = 2, shape = 4),
    qinvgauss(c(0.25, 0.75), mean = 1, dispersion = c(0.2, 0.8)),
    qinvgauss(c(0.25, 0.75), mean = 1, dispersion = c(0.2, 0.8), lower.tail = FALSE),
    qinvgauss(0.99, mean = 1, dispersion = 1e-10),
    qinvgauss(0.5, mean = Inf, dispersion = 0.5),
    as.numeric(qinvgauss(matrix(c(0.3, 0.7), nrow = 2), mean = 1, dispersion = 0.5))
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
