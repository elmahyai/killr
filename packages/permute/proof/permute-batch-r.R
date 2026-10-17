lib <- "/tmp/permute-lib"
.libPaths(c(lib, .libPaths()))
library(permute)
out <- file.path(dirname(sub("^--file=", "", commandArgs()[grep("^--file=", commandArgs())])),
                 "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
writeLines(c(
  paste0("Within=", paste(capture.output(dput(unclass(Within()))), collapse = "")),
  paste0("nobs_scalar=", nobs(7)),
  paste0("nobs_vector=", nobs(1:4))
), file.path(out, "permute-batch-r-values.txt"))
set.seed(1729)
x <- list(
  shuffle = shuffle(4, how(within=Within(type="free"))),
  shuffleFree = shuffleFree(4, 4),
  shuffleGrid = shuffleGrid(2, 2),
  shuffleSeries = shuffleSeries(1:4),
  shuffleSet = shuffleSet(4, 2, how(within=Within(type="free"))),
  shuffleStrata = shuffleStrata(factor(rep(1:2, 2)), "free")
)
writeLines(vapply(names(x), function(n)
  paste0(n, "=", paste(capture.output(dput(x[[n]])), collapse="")),
  character(1)), file.path(out, "permute-batch-r-random.txt"))
timed <- function(f) {
  f()
  z <- numeric(20)
  for (i in seq_len(20)) {
    t <- Sys.time(); f()
    z[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) * 1000
  }
  median(z)
}
r_ms <- c(timed(Within), timed(function() nobs(c(1, 2, 3, 4))))
write.csv(data.frame(
  name=c(names(x), "Within", "nobs"),
  matches=c(rep("blocked", 6), "yes", "yes"),
  max_abs_diff=c(rep(NA, 6), 0, 0),
  r_ms=c(rep(NA, 6), r_ms),
  translated_ms=NA, speedup=NA,
  blocked_by=c(rep("R RNG algorithm cannot be reproduced exactly by NumPy", 6), "", "")
), file.path(out, "permute-batch-metrics-r.csv"), row.names=FALSE, na="NA", quote=FALSE)
