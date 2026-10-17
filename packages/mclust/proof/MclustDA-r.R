.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
x <- matrix(c(1, 1.1, 1.2, 2, 2.1, 2.2, 4, 4.1, 4.2), ncol = 1)
y <- factor(c("a", "a", "a", "b", "b", "b", "c", "c", "c"))
one <- function() {
  fit <- MclustDA(x, y, modelType = "EDDA", modelNames = "E", verbose = FALSE)
  c(fit$n, fit$d, unname(unlist(fit$prop)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
