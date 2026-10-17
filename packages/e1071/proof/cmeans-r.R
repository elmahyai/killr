.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  set.seed(4242)
  x <- matrix(c(0, 0, 3, 0, 0, 4, 6, 6, 1, 2, 5, 5), ncol = 2, byrow = TRUE)
  centers <- matrix(c(0, 0, 5, 5, 3, 4), ncol = 2, byrow = TRUE)
  fit <- cmeans(x, centers, iter.max = 50, m = 2, dist = "euclidean", method = "cmeans")
  c(
    as.numeric(fit$membership),
    as.numeric(fit$centers),
    as.numeric(fit$cluster),
    as.numeric(fit$size),
    fit$iter,
    fit$withinerror
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
