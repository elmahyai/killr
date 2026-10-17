.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

incidence <-
  matrix(c(1, 1, 2, 2, 2, 1, 3, 2, 0), ncol = 3, byrow = TRUE,
         dimnames = list(NULL, c("Par", "From", "To")))

one <- function() {
  as.vector(LDEsysMat(c(1.2, 0.3, 0.4), incidence))
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
