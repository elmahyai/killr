.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
X <- as.matrix(read.csv(file.path(proof, "MclustSSC_X.csv")))
cl <- read.csv(file.path(proof, "MclustSSC_class.csv"))[[1L]]

one <- function() {
  mod <- MclustSSC(X, cl, verbose = FALSE)
  c(
    as.numeric(mod$G),
    mod$loglik,
    mod$df,
    mod$bic,
    as.numeric(mod$z),
    as.numeric(mod$parameters$pro),
    as.numeric(mod$parameters$mean)
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
