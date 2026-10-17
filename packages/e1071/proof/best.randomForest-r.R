.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({library(e1071); library(randomForest)})
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
X <- matrix(c(0.0, 1.0, 1.2, 0.8, 2.5, 2.7, 2.8, 2.4, 0.1, 0.9, 2.6, 2.5,
              0.4, 1.6, 1.9, 0.3, 2.2, 2.9, 0.7, 0.2, 1.5, 1.1, 2.9, 2.0),
            ncol = 2, byrow = TRUE)
Y <- factor(c("a", "a", "b", "b", "a", "b", "a", "a", "b", "a", "a", "b"))
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
one <- function() {
  set.seed(4242)
  res <- best.randomForest(X, y = Y, nodesize = c(1, 3), mtry = c(1, 2), ntree = 25,
                           tunecontrol = tune.control(cross = 3))
  pred <- predict(res, X)
  c(as.integer(pred), as.integer(res$predicted))
}
value <- one()
cat("best.randomForest codes on X, then OOB predicted codes:\n")
cat(sprintf("%.6g", value), "\n")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf('{"value":%s,"median_ms":%.17g}', json_num(value), median(elapsed) * 1000),
           "packages/e1071/proof/best.randomForest-r-out.json")
