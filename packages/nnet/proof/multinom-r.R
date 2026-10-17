.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nnet))
if (packageDescription("nnet")$Version != "7.3-21") stop("expected nnet 7.3-21")
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse=","), "]")

one <- function() {
  df <- data.frame(y=factor(c("a","b","a","c","b","c")), x=c(0, 1, 0.2, 0.8, 0.4, 0.9))
  fit <- multinom(y ~ x, df, maxit=40, trace=FALSE)
  c(fit$wts, fit$deviance, fit$AIC)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
