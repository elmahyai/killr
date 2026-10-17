.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
x <- list(G = 2); class(x) <- "densityMclust"
one <- function() as.Mclust.densityMclust(x)$G
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat(sprintf("%.17g\n", value)); cat(sprintf("%.17g\n", median(elapsed) * 1000))
