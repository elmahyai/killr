.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

data(CO2, package = "datasets")

one <- function() {
  fm1 <- nlsList(
    uptake ~ SSasympOff(conc, Asym, lrc, c0) | Plant,
    CO2,
    start = c(Asym = 30, lrc = -4.5, c0 = 52)
  )
  as.numeric(unlist(coef(fm1)))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
