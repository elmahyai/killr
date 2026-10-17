.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  set.seed(4242)
  x <- matrix(c(0, 0, 3, 0, 0, 4, 6, 6, 1, 2, 5, 5), ncol = 2, byrow = TRUE)
  bc <- bclust(
    x, 2,
    iter.base = 2,
    base.centers = 3,
    verbose = FALSE,
    resample = FALSE
  )
  c(
    as.numeric(bc$cluster),
    as.numeric(bc$centers),
    as.numeric(bc$allcenters),
    as.numeric(bc$members),
    as.numeric(bc$hclust$height)
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
