.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

make_mclust_da <- function() {
  models <- list(
    setosa = list(n = 50L, modelName = "EEE", G = 2L),
    versicolor = list(n = 50L, modelName = "XXX", G = 1L),
    virginica = list(n = 50L, modelName = "XXX", G = 1L)
  )
  structure(list(models = models, type = "MclustDA", n = 150L, d = 4L),
            class = "MclustDA")
}

one <- function() capture.output(print(make_mclust_da()))
value <- one()
cat(value, sep = "\n")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
