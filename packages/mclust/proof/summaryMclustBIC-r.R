.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
object <- matrix(-15.016671193134002, nrow = 1, dimnames = list("1", "X"))
attr(object, "initialization") <- list()
attr(object, "control") <- emControl()
one <- function() {
  z <- summaryMclustBIC(object, data = matrix(1:4, ncol = 1))
  c(z$modelName, z$G, z$n, z$d, z$bic, z$loglik, z$classification, z$uncertainty)
}
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "|"), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
