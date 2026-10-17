.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
p <- matrix(c(-1, -3, -2, 2, 3, 4), nrow = 2, byrow = TRUE)
attr(p, "class") <- "hc"
attr(p, "model") <- "EII"
attr(p, "initialPartition") <- 1:4
attr(p, "data") <- matrix(1:4, nrow = 4, dimnames = list(as.character(1:4), "x"))
one <- function() {
  z <- as.hclust.hc(p, what = "merge", labels = FALSE)
  c(as.vector(z$merge), z$height, z$order)
}
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = ""); cat(sprintf("%.17g\n", median(elapsed) * 1000))
