.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  OrthoMat <- asTable(Orthodont)
  Orth2 <- balancedGrouped(
    distance ~ age | Subject,
    data = OrthoMat,
    labels = list(
      x = "Age",
      y = "Distance from pituitary to pterygomaxillary fissure"
    ),
    units = list(x = "(yr)", y = "(mm)")
  )
  c(
    as.numeric(Orth2$distance),
    as.numeric(Orth2$age),
    as.numeric(Orth2$Subject)
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
