.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

make_mclust_da <- function() {
  sigma <- matrix(c(1.2, 0.25, 0.25, 0.8), 2, 2)
  chol <- t(chol(sigma))
  model <- function(mean) list(
    n = 50L, modelName = "EEE", G = 1L,
    parameters = list(
      pro = 1, mean = matrix(mean, 2, 1),
      variance = list(modelName = "EEE", d = 2L, G = 1L,
                      sigma = array(sigma, c(2, 2, 1)),
                      Sigma = sigma, cholSigma = chol)
    )
  )
  structure(list(
    models = list(alpha = model(c(0, 0)), beta = model(c(3, 2))),
    prop = c(alpha = 0.3, beta = 0.7),
    data = matrix(c(0, 0, 1, 1, 2, 1, 3, 2, 4, 3, -1, 0), 6, 2, byrow = TRUE),
    type = "MclustDA", n = 6L, d = 2L
  ), class = "MclustDA")
}

fit <- make_mclust_da()
newdata <- matrix(c(-1, 0, 0, 0, 1, 1, 2, 1, 3, 2, 4, 3), 6, 2, byrow = TRUE)
one <- function() predict(fit, newdata = newdata)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(as.character(value$classification), sep = "\n")
cat(sprintf("%.17g\n", as.numeric(value$z)), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
