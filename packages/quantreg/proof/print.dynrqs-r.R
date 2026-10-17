suppressPackageStartupMessages({library(quantreg); library(zoo)})
uk <- log10(UKDriverDeaths)
ap <- log(AirPassengers)
hdr <- function(x) {
  t <- as.numeric(index.dynrq(x))
  f <- 12
  y1 <- floor(t[1] + 1e-5); y2 <- floor(t[length(t)] + 1e-5)
  c(y1, round((t[1] - y1) * f) + 1, y2, round((t[length(t)] - y2) * f) + 1)
}
one <- function() {
  d3 <- suppressWarnings(dynrq(uk ~ L(uk, 1) + L(uk, 12), tau = 1:3/4))
  fm <- suppressWarnings(dynrq(ap ~ trend(ap) + season(ap), tau = 1:4/5))
  invisible(capture.output(print(d3)))
  invisible(capture.output(print(fm)))
  n1 <- NROW(residuals(d3)); n2 <- NROW(residuals(fm))
  c(hdr(d3), as.numeric(coef(d3)), n1, n1 - nrow(coef(d3)),
    hdr(fm), as.numeric(coef(fm)), n2, n2 - nrow(coef(fm)))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
