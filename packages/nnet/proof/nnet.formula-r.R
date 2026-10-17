.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nnet))
if (packageDescription("nnet")$Version != "7.3-21") stop("expected nnet 7.3-21")
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse=","), "]")

one <- function() {
  w <- c(0.1, -0.2, 0.3, 0, 0.4, -0.1, 0.2, 0.5, -0.3)
  df <- data.frame(y=c(0.2, 0.8, 0.4, 0.9), x1=c(0, 1, 0.5, 1), x2=c(1, 0, 0.5, 1))
  as.numeric(nnet(y ~ x1 + x2, df, size=2, linout=TRUE, decay=0.01, Wts=w, maxit=30, trace=FALSE)$wts)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
