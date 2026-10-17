suppressPackageStartupMessages(library(mvtnorm))
fmt <- function(x) {
  if (is.logical(x) && length(x) == 1) return(if (isTRUE(x)) "1" else "0")
  paste(sprintf("%.16g", as.numeric(x)), collapse = " ")
}
one <- function() {
  as.numeric(pmvnorm(lower = -Inf, upper = 3, mean = 0, sigma = 1))
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
