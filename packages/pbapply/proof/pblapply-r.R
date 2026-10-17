suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

one <- function() {
  op <- pboptions(type = "none", nout = 3)
  on.exit(pboptions(op))
  x <- as.list(1:10)
  out <- unlist(pblapply(x, function(i) i * i))
  c(out, length(pblapply(integer(0), identity)))
}

quiet_one <- function() {
  capture.output(v <- one(), type = "output")
  v
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  quiet_one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, sprintf, character(1), fmt = "%.17g")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
