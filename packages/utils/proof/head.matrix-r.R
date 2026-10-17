one <- function() {
  paste(as.vector(head(matrix(1:12, nrow=4), 2)), collapse=",")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sep="")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
