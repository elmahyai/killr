suppressPackageStartupMessages(library(mvtnorm))
fmt <- function(x) {
  if (is.logical(x) && length(x) == 1) return(if (isTRUE(x)) "1" else "0")
  paste(sprintf("%.16g", as.numeric(x)), collapse = " ")
}
one <- function() {
  B <- matrix(c(1, 0, 0.5, 1), 2)
  Z <- matrix(c(0, 0.5, -0.5, 1), 2)
  as.numeric(lpRR(lower = c(-1, -1), upper = c(1, 1), B = B, Z = Z))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(fmt(value), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
