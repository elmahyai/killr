.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

make_min_mclust_da <- function() {
  models <- list(
    setosa = list(
      n = 50L, G = 1L, modelName = "EEE",
      parameters = list(
        pro = c(1),
        mean = matrix(5:8, 4, 1, dimnames = list(c("SL", "SW", "PL", "PW"), NULL)),
        variance = list(
          d = 4L, G = 1L,
          sigma = array(diag(c(0.1, 0.2, 0.3, 0.4)), dim = c(4, 4, 1)),
          Sigma = diag(4) * 0.1
        )
      )
    ),
    versicolor = list(
      n = 50L, G = 1L, modelName = "EEE",
      parameters = list(
        pro = NULL,
        mean = matrix(9:12, 4, 1),
        variance = list(
          d = 4L, G = 1L,
          sigma = array(diag(c(0.5, 0.6, 0.7, 0.8)), dim = c(4, 4, 1)),
          Sigma = diag(4) * 0.5
        )
      )
    )
  )
  structure(
    list(models = models, type = "EDDA", n = 100L, d = 4L),
    class = "MclustDA"
  )
}

flatten_get_parameters <- function(par) {
  out <- length(par)
  for (i in seq_along(par)) {
    el <- par[[i]]
    if (is.list(el)) {
      if (!is.null(el$pro)) out <- c(out, as.numeric(el$pro))
      out <- c(out, as.numeric(el$mean))
      out <- c(out, as.numeric(el$variance))
    } else {
      out <- c(out, as.numeric(el))
    }
  }
  out
}

one <- function() flatten_get_parameters(getParameters.MclustDA(make_min_mclust_da()))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
