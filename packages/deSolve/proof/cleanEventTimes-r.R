.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
events <- sort(c(0, 2, 3, 4 + 1e-10, 5, 7 - 1e-10,
                 7 + 6e-15, 7.5, 9, 24.9999, 25, 80, 1001, 1e300))
times <- sort(c(0, 1:7, 4.5, 6.75, 7.5, 9.2, 9.0001, 25, 879, 1e3, 1e300 + 5))
one <- function() {
  cleanEventTimes(times, events)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
