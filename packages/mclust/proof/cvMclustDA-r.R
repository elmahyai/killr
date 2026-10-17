.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

one <- function() {
  set.seed(42)
  Class <- iris$Species
  X <- as.matrix(iris[, 1:4])
  irisEDDA <- MclustDA(X, Class, modelType = "EDDA", modelNames = "EEE", verbose = FALSE)
  set.seed(42)
  cv <- cvMclustDA(irisEDDA, nfold = 10, verbose = FALSE)
  c(
    cv$ce, cv$se.ce, cv$brier, cv$se.brier,
    as.numeric(cv$classification),
    as.numeric(cv$z)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
