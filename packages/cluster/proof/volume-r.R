.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(cluster))
if (packageDescription("cluster")$Version != "2.1.8.3") stop("expected cluster 2.1.8.3")
options(warn = -1)
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse=","), "]")
x <- matrix(c(1,2, 1.2,1.8, 1.1,2.2, 5,8, 5.5,7.5, 4.8,8.2, 9,1, 8.5,1.5, 8.2,1.2, 5.2,7.8), ncol=2, byrow=TRUE)

one <- function() {
  eh <- ellipsoidhull(x)
  c(volume(eh), volume(eh, log = TRUE))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
