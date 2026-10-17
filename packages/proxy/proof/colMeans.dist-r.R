.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(proxy))
if (packageDescription("proxy")$Version != "0.4-29") stop("expected proxy 0.4-29")
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse=","), "]")

one <- function() {
  x <- matrix(c(1,2, 3,6, 4,8, 7,1), ncol=2, byrow=TRUE)
  colMeans.dist(dist(x))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
