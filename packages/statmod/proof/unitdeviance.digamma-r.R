suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  mus <- exp(seq(log(0.01), log(1000), length.out = 50))
  ratios <- rep(c(0.5, 0.8, 1.0, 1.05, 1.1, 2.0), length.out = 50)
  y <- mus * ratios
  c(
    unitdeviance.digamma(y, mus),
    unitdeviance.digamma(c(0.25, 1.5, 7.5), c(0.3, 1.4, 8.0))
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
