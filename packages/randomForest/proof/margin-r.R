.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(randomForest))
if (packageDescription("randomForest")$Version != "4.7-1.2") stop("expected randomForest 4.7-1.2")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

one <- function() {
  as.numeric(margin(matrix(c(0.7,0.3, 0.2,0.8, 0.4,0.6), ncol=2, byrow=TRUE, dimnames=list(NULL, c("a","b"))), factor(c("a","b","a"))))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
