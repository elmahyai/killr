.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat_result <- function(r) {
  c(r$numiter, r$where, r$value)
}

one <- function() {
  fun <- function(X) {
    ifelse(LETTERS[X] > "M", 1, ifelse(LETTERS[X] < "M", -1, 0))
  }
  c(
    flat_result(binsearch(function(x) x - 10, range = c(0, 20))),
    flat_result(binsearch(function(x) x - 10.1, range = c(0, 20))),
    flat_result(binsearch(fun, range = 1:26)),
    flat_result(suppressWarnings(binsearch(function(x) x - 25, range = c(0, 20))))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(format(value, digits = 17), collapse = ","), median(elapsed) * 1000))
