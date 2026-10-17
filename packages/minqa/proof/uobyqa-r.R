.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(minqa))
fr <- function(x) 100 * (x[2] - x[1]^2)^2 + (1 - x[1])^2
one <- function() uobyqa(c(1, 2), fr)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE\n")
cat(sprintf("%.17g\n", c(value$par, value$fval)))
cat(value$feval, "\n", sep = "")
cat(value$ierr, "\n", sep = "")
cat(value$msg, "\n", sep = "")
cat("<<<END>>>\n")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
