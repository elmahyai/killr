
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(randomForest))
if (packageDescription("randomForest")$Version != "4.7-1.2") stop("expected randomForest 4.7-1.2")
options(warn = -1)
json_num <- function(x) {
  x <- as.numeric(x)
  x[is.na(x)] <- -1
  paste0("[", paste(sprintf("%.17g", x), collapse=","), "]")
}
y <- c(1.2, 0.4, 2.1, 1.7, 0.2, 3.3, 2.8, 0.9, 1.1, 4.0, 0.5, 2.2, 1.8, 3.1, 0.7, 2.6, 1.4, 0.3, 3.6, 2.0)
x <- matrix(c(1:60)/7, nrow=20, ncol=3)
newx <- matrix(c(2,9, 15,22, 30,41)/7, nrow=2)
xc <- matrix(c(1:48)/5, nrow=16, ncol=3)
yc <- factor(rep(c("b","a","b","a"), each=4))
reg <- function() randomForest(x, y, ntree=3, mtry=2, nodesize=5, importance=TRUE)

one <- function() {
  set.seed(6)
  cv <- rfcv(x, y, cv.fold=3, ntree=3, step=0.5)
  c(cv$n.var, cv$error.cv, unlist(cv$predicted))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
