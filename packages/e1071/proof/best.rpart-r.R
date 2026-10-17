.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({library(e1071); library(rpart)})
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
x1 <- c(0.0, 1.2, 2.5, 2.8, 0.1, 2.6, 0.4, 1.9, 2.2, 0.7, 1.5, 2.9)
x2 <- c(1.0, 0.8, 2.7, 2.4, 0.9, 2.5, 1.6, 0.3, 2.9, 0.2, 1.1, 2.0)
y <- as.numeric(c("a", "a", "b", "b", "a", "b", "a", "a", "b", "a", "a", "b") == "b")
dat <- data.frame(y = y, x1 = x1, x2 = x2)
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
one <- function() {
  set.seed(4242)
  res <- best.rpart(y ~ x1 + x2, data = dat, minsplit = c(3, 5), cp = c(0.01, 0.1), xval = 0,
                    tunecontrol = tune.control(cross = 3))
  pred <- predict(res, dat)
  c(as.numeric(pred), as.numeric(res$frame$n), as.numeric(res$frame$yval))
}
value <- one()
cat("best.rpart predictions on dat, node n, node yval:\n")
cat(sprintf("%.6g", value), "\n")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf('{"value":%s,"median_ms":%.17g}', json_num(value), median(elapsed) * 1000),
           "packages/e1071/proof/best.rpart-r-out.json")
