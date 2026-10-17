suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

one <- function() {
  mats <- list(
    combMat(5, 2, 4),
    combMat(5, 4, 2),
    combMat(3, 1, 2),
    combMat(6, 2, 5),
    combMat(4, 1, 1),
    combMat(5, numeric(0), 3),
    combMat(5, 2, numeric(0))
  )
  unlist(lapply(mats, as.vector))
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
