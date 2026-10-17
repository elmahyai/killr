.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

data(Orthodont, package = "nlme")
fm1 <- lmList(Orthodont)
fm2 <- lme(fm1)
ortho3 <- Orthodont[, c("distance", "age", "Subject")]

one <- function() {
  c(
    as.vector(as.matrix(ranef(fm2))),
    as.vector(as.matrix(ranef(fm2, augFrame = TRUE, data = ortho3))),
    as.vector(as.matrix(ranef(fm2, standard = TRUE))),
    as.vector(as.matrix(ranef(fm1)))
  )
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
