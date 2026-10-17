.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({library(e1071); library(nnet)})
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
X <- matrix(c(0.0, 1.0, 1.2, 0.8, 2.5, 2.7, 2.8, 2.4, 0.1, 0.9, 2.6, 2.5,
              0.4, 1.6, 1.9, 0.3, 2.2, 2.9, 0.7, 0.2, 1.5, 1.1, 2.9, 2.0),
            ncol = 2, byrow = TRUE)
Y <- as.numeric(c("a", "a", "b", "b", "a", "b", "a", "a", "b", "a", "a", "b") == "b")
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
one <- function() {
  set.seed(4242)
  res <- tune.nnet(X, Y, size = c(2, 3), decay = c(0, 0.1), trace = FALSE,
                   tunecontrol = tune.control(cross = 3, nrepeat = 2, performances = TRUE))
  c(
    res$best.performance,
    as.numeric(res$best.parameters$size),
    as.numeric(res$best.parameters$decay),
    as.numeric(res$performances$size),
    as.numeric(res$performances$decay),
    as.numeric(res$performances$error),
    as.numeric(res$performances$dispersion)
  )
}
value <- one()
cat("tune.nnet best error, best size, best decay, grid size, decay, error, dispersion:\n")
cat(sprintf("%.6g", value), "\n")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf('{"value":%s,"median_ms":%.17g}', json_num(value), median(elapsed) * 1000),
           "packages/e1071/proof/tune.nnet-r-out.json")
