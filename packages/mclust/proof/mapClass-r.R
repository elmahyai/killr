suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

flatten <- function(out) {
  c(unlist(out$aTOb), unlist(out$bTOa))
}

one <- function() {
  a <- c(1, 1, 2, 2, 3)
  b <- c(1, 2, 2, 3, 3)
  flatten(mapClass(a, b))
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
