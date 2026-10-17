.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  OrthoMat <- asTable(Orthodont)
  Orth2 <- balancedGrouped(
    distance ~ age | Subject,
    data = OrthoMat,
    labels = list(x = "Age", y = "Distance"),
    units = list(x = "(yr)", y = "(mm)")
  )
  fm1 <- lme(distance ~ age, data = Orthodont, subset = Sex == "Female")
  c(
    as.numeric(getGroups(Orth2)),
    as.numeric(getGroups(Orthodont, distance ~ age | Subject)),
    as.numeric(getGroups(fm1))
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
