.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
x <- list(data = matrix(c(-2, -1, 1, 2), ncol = 1),
          modelName = "EII", parameters = list(pro = c(.4, .6),
          mean = matrix(c(-1, 1), nrow = 1),
          variance = list(modelName = "EII", d = 1, G = 2, sigmasq = 1)),
          G = 2)
class(x) <- "Mclust"
one <- function() as.densityMclust.Mclust(x)$density
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat(sprintf("%.17g\n", value)); cat(sprintf("%.17g\n", median(elapsed) * 1000))
