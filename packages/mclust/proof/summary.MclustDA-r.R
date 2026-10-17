.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

make_mclust_da <- function() {
  x <- matrix(c(-1, -1, 0, 0, 2, 2, 3, 3), 4, 2, byrow = TRUE)
  make_model <- function(mean, s) list(
    n = 2L, d = 2L, G = 1L, modelName = "EII",
    parameters = list(
      pro = 1, mean = matrix(mean, 2, 1),
      variance = list(
        d = 2L, G = 1L, sigma = array(diag(2) * s, c(2, 2, 1)),
        Sigma = diag(2) * s, sigmasq = s
      )
    )
  )
  structure(list(
    models = list(A = make_model(c(0, 0), 1), B = make_model(c(3, 3), 2)),
    type = "EDDA", n = 4L, d = 2L, prop = c(A = .5, B = .5),
    data = x, class = factor(c("A", "A", "B", "B")),
    loglik = -12.5, df = 8L, bic = 1.25
  ), class = "MclustDA")
}

one <- function() summary.MclustDA(make_mclust_da())
value <- one()
cat(value$type, "\n", sep = "")
cat(paste(value$n, collapse = ","), "\n", sep = "")
cat(paste(value$classes, collapse = ","), "\n", sep = "")
cat(paste(value$G, collapse = ","), "\n", sep = "")
cat(paste(value$modelName, collapse = ","), "\n", sep = "")
cat(sprintf("%.17g %.17g\n", value$ce, value$brier))
cat(paste(as.vector(value$tab), collapse = ","), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
