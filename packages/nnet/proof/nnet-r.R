.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nnet))
if (packageDescription("nnet")$Version != "7.3-21") stop("expected nnet 7.3-21")
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse=","), "]")

one <- function() {
  x <- matrix(c(0,1, 1,0, 0.5,0.5, 1,1, 0.2,0.8), ncol=2, byrow=TRUE)
  y <- matrix(c(1,0, 0,1, 1,0, 0,1, 1,0), ncol=2, byrow=TRUE)
  as.numeric(nnet(x, y, size=2, softmax=TRUE, decay=0.01, Wts=rep(0.1, 12), maxit=20, trace=FALSE)$wts)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
