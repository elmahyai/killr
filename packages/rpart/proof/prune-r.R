
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rpart))
suppressPackageStartupMessages(library(survival))
if (packageDescription("rpart")$Version != "4.1.27") stop("expected rpart 4.1.27")
options(warn = -1)
json_num <- function(x) {
  x <- as.numeric(x)
  x <- x[is.finite(x)]
  paste0("[", paste(sprintf("%.17g", x), collapse=","), "]")
}
y30 <- c(1.2, 0.4, 2.1, 1.7, 0.2, 3.3, 2.8, 0.9, 1.1, 4.0,
         0.5, 2.2, 1.8, 3.1, 0.7, 2.6, 1.4, 0.3, 3.6, 2.0,
         5.1, 0.8, 4.4, 1.5, 6.2, 2.9, 0.6, 3.8, 1.9, 4.7)
x1 <- (1:30)/3
x1[5] <- NA
x2 <- c(5,1,8,2,9,3,7,4,6,2, 1,8,3,9,4,7,2,6,5,1, 9,3,8,2,7,4,6,1,5,3)
x3 <- (30:1)/4
df30 <- data.frame(y=y30, x1=x1, x2=x2, x3=x3)
ctrl30 <- rpart.control(minsplit=8, minbucket=3, cp=0.01, xval=5, maxdepth=10)
fit30 <- function() {
  set.seed(1)
  rpart(y ~ ., df30, control=ctrl30, x=TRUE, y=TRUE)
}
y12 <- c(1,2,1.2, 5,4.5,5.5, 8,9,7.5, 3,3.2,2.8)
df12 <- data.frame(y=y12, x1=c(1,2,3, 6,7,8, 12,13,14, 4,5,9), x2=c(2,2,1, 0,1,0, 5,4,6, 3,3,2))
w12 <- c(1,1,2, 1,3,1, 2,1,1, 1,1,4)
fit12 <- function() {
  set.seed(11)
  rpart(y ~ ., df12, weights=w12, control=rpart.control(minsplit=4, minbucket=2, cp=0.001, xval=4, maxdepth=6), x=TRUE, y=TRUE)
}

one <- function() {
  pr <- prune(fit30(), cp=0.05)
  c(pr$frame$yval, pr$where, as.numeric(pr$cptable), pr$variable.importance)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
