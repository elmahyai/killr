.libPaths(c("/tmp/r-lib", .libPaths()))
library(conflicted)
run <- function() unclass(conflict_scout("base"))
run()
times <- numeric(20)
for (i in seq_along(times)) {
  started <- Sys.time(); run()
  times[[i]] <- as.numeric(difftime(Sys.time(), started, units = "secs")) * 1000
}
cat("result={}\n"); cat(sprintf("r_ms=%.9f\n", median(times)))
