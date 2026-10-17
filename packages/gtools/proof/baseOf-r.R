.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (length(x) == 0) return(numeric(0))
  if (is.matrix(x)) return(as.numeric(x))
  as.numeric(x)
}

one <- function() {
  c(
    flat(baseOf(123)),
    flat(baseOf(123, base = 2)),
    flat(baseOf(123, base = 8)),
    flat(baseOf(123, base = 16)),
    flat(baseOf(123, len = 5)),
    flat(baseOf(c(0, 1, 255, 256), base = 2, len = 4)),
    flat(baseOf(c(5, 123, 4096), base = 16)),
    flat(baseOf(c(10, 1000), base = 10)),
    flat(baseOf(integer(0)))
  )
}

one()
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(value, collapse = ","), median(elapsed) * 1000))
