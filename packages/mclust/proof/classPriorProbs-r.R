.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
set.seed(42)
I <- iris$Species %in% c("setosa", "versicolor")
Class <- droplevels(iris$Species[I])
X <- as.matrix(iris[I, 1:4])
fit <- MclustDA(X, Class, modelType = "EDDA", modelNames = "EEE", verbose = FALSE)

value <- as.numeric(classPriorProbs(fit))

one <- function() as.numeric(classPriorProbs(fit))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
