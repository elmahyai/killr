.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
object <- matrix(100, nrow = 1, dimnames = list("0", "X"))
attr(object, "initialization") <- list(noise = TRUE)
attr(object, "Vinv") <- 1
one <- function() {
  z <- summaryMclustBICn(object, data = c(1, 2, 3, 4))
  c(z$modelName, z$G, z$n, z$bic, z$loglik, z$classification, z$uncertainty)
}
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "|"), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
