suppressPackageStartupMessages({library(quantreg); library(zoo)})
uk <- log10(UKDriverDeaths)
hdr <- function(x) {
  t <- as.numeric(index.dynrq(x))
  f <- 12
  y1 <- floor(t[1] + 1e-5); y2 <- floor(t[length(t)] + 1e-5)
  c(y1, round((t[1] - y1) * f) + 1, y2, round((t[length(t)] - y2) * f) + 1)
}
one <- function() {
  a <- suppressWarnings(dynrq(uk ~ L(uk, 1) + L(uk, 12)))
  se <- suppressWarnings(dynrq(uk ~ L(uk, 1) + L(uk, 12), start = c(1975, 1), end = c(1982, 12)))
  invisible(capture.output(print(a)))
  invisible(capture.output(print(se)))
  n1 <- NROW(residuals(a)); n2 <- NROW(residuals(se))
  c(hdr(a), as.numeric(coef(a)), n1, n1 - length(coef(a)),
    hdr(se), as.numeric(coef(se)), n2, n2 - length(coef(se)))
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
