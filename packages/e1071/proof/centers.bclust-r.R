.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
x <- matrix(c(1, 2, 1.2, 1.8, 1.1, 2.2, 5, 8, 5.5, 7.5, 4.8, 8.2,
              9, 1, 8.5, 1.5, 8.2, 1.2, 5.2, 7.8, 3, 3, 3.1, 2.9,
              0.5, 6, 7, 4, 6.5, 3.5), ncol = 2, byrow = TRUE)
set.seed(1)
bc <- bclust(x, 3, iter.base = 4, base.centers = 4, verbose = FALSE, resample = FALSE)
one <- function() {
  c(
    as.numeric(centers.bclust(bc, 2)),
    as.numeric(centers.bclust(bc, 3)),
    as.numeric(centers.bclust(bc, 4))
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
