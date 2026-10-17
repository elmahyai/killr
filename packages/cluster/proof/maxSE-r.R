.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(cluster))
if (packageDescription("cluster")$Version != "2.1.8.3") stop("expected cluster 2.1.8.3")
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse=","), "]")

one <- function() {
  f <- c(0.1, 0.4, 0.35, 0.5)
  se <- c(0.05, 0.05, 0.05, 0.05)
  c(maxSE(f, se, "firstmax"), maxSE(f, se, "globalmax"), maxSE(f, se, "Tibs2001SEmax"),
    maxSE(f, se, "firstSEmax"), maxSE(f, se, "globalSEmax"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
