.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(urca))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)
data(ecb)
m3.real <- ecb[, "m3"] / ecb[, "gdp.defl"]
gdp.real <- ecb[, "gdp.nom"] / ecb[, "gdp.defl"]
rl <- ecb[, "rl"]
ecb.data <- cbind(m3.real, gdp.real, rl)

one <- function() {
  obj <- ca.po(ecb.data, type = "Pz")
  est <- unlist(lapply(obj@testreg, function(s) s$coefficients[, 1]))
  se <- unlist(lapply(obj@testreg, function(s) s$coefficients[, 2]))
  c(as.numeric(obj@teststat), obj@lag, as.numeric(obj@cval), est, se)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
