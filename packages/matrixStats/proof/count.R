set.seed(1)
x <- matrix(rnorm(400 * 250), nrow = 400, ncol = 250)
writeBin(as.numeric(x), "/tmp/ms-proof-count-x.bin")

encode <- function(v) {
  v <- as.vector(v)
  if (is.logical(v)) {
    ifelse(is.na(v), "NA", ifelse(v, "T", "F"))
  } else if (is.integer(v)) {
    ifelse(is.na(v), "NA", as.character(v))
  } else {
    ifelse(is.na(v), "NA", sprintf("%.17g", v))
  }
}

one <- function() matrixStats::count(as.vector(x))
ans <- one()
writeLines(encode(ans), "/tmp/ms-proof-count-ans.txt")

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(median(elapsed) * 1000, "\n")
