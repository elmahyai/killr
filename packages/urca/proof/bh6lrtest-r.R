.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(urca))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)
data(UKpppuip)
dat1 <- as.matrix(UKpppuip[, c("p1", "p2", "e12", "i1", "i2")])
dat2 <- as.matrix(UKpppuip[, c("doilp0", "doilp1")])

one <- function() {
  h1 <- ca.jo(dat1, type = "trace", K = 2, season = 4, dumvar = dat2)
  h6 <- matrix(c(1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0), ncol = 3)
  res <- bh6lrtest(z = h1, H = h6, r = 2, r1 = 1, conv.val = 0.0001, max.iter = 50)
  c(res@teststat, res@pval, res@lambda[1], as.numeric(res@V), as.numeric(res@W))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
