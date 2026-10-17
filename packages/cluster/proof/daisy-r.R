.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(cluster))
if (packageDescription("cluster")$Version != "2.1.8.3") stop("expected cluster 2.1.8.3")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

one <- function() {
  x <- matrix(c(1,2, 3,6, 4,8, 7,1), ncol=2, byrow=TRUE); c(as.numeric(daisy(x)), as.numeric(daisy(x, metric="manhattan")), as.numeric(daisy(x, metric="gower")), as.numeric(daisy(x, stand=TRUE)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
