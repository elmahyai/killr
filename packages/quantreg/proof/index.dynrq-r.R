suppressPackageStartupMessages({library(quantreg); library(zoo)})
uk <- log10(UKDriverDeaths)
one <- function() {
  a <- suppressWarnings(dynrq(uk ~ L(uk, 1) + L(uk, 12)))
  se <- suppressWarnings(dynrq(uk ~ L(uk, 1) + L(uk, 12), start = c(1975, 1), end = c(1982, 12)))
  c(as.numeric(index.dynrq(a)), as.numeric(index.dynrq(se)))
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
