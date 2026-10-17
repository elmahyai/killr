.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(class))
if (packageDescription("class")$Version != "7.3-24") stop("expected class 7.3-24")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  as.integer(knn.cv(matrix(c(0,0, 1,0, 0,3, 10,0), ncol=2, byrow=TRUE), factor(c("a","b","a","b")), k=1))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
