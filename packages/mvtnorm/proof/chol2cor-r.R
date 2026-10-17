suppressPackageStartupMessages(library(mvtnorm))
fmt <- function(x) {
  if (is.logical(x) && length(x) == 1) return(if (isTRUE(x)) "1" else "0")
  paste(sprintf("%.16g", as.numeric(x)), collapse = " ")
}
one <- function() {
  as.numeric(unclass(chol2cor(as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE)))))
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
