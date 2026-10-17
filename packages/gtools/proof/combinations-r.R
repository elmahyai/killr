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
    flat(combinations(15, 4)),
    flat(combinations(6, 3, repeats.allowed = TRUE)),
    flat(combinations(10, 3))
  )
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(value, collapse = ","), median(elapsed) * 1000))
