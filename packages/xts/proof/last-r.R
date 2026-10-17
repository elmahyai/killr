suppressPackageStartupMessages(library(xts))
one <- function() {
  paste(last(1:10, 3), collapse=",")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
if (is.logical(value)) cat(if (value) "TRUE\n" else "FALSE\n") else cat(value, "\n", sep="")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
