suppressPackageStartupMessages({library(quantreg); library(zoo)})
uk <- log10(UKDriverDeaths)
d3 <- suppressWarnings(dynrq(uk ~ L(uk, 1) + L(uk, 12), tau = 1:3/4))
one <- function() {
  s3 <- summary(d3, se = "nid")
  invisible(capture.output(print(s3[[1]])))
  c(1, NROW(d3$residuals), as.numeric(s3[[1]]$coefficients))
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
