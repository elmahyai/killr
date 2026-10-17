suppressPackageStartupMessages(library(mvtnorm))
fmt <- function(x) {
  if (is.logical(x) && length(x) == 1) return(if (isTRUE(x)) "1" else "0")
  paste(sprintf("%.16g", as.numeric(x)), collapse = " ")
}
one <- function() {
  m <- mvnorm(chol = as.chol(ltMatrices(c(1, 0.3, 1), diag = TRUE)))
  as.numeric(unclass(condDist(m, which_given = 1, given = matrix(0, 1))$scale))
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
