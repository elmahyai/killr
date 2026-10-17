.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  OrthoMat <- asTable(Orthodont)
  Orth2 <- balancedGrouped(
    distance ~ age | Subject,
    data = OrthoMat,
    labels = list(x = "Age", y = "Distance"),
    units = list(x = "(yr)", y = "(mm)")
  )
  paste(
    deparse(getResponseFormula(y ~ x | g)),
    deparse(getResponseFormula(y ~ x)),
    deparse(getResponseFormula(y ~ x + z | g)),
    deparse(getResponseFormula(log(y) ~ x)),
    deparse(getResponseFormula((y1 + y2) ~ x)),
    deparse(getResponseFormula(Orth2)),
    sep = ";"
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
escaped <- gsub("\\\\", "\\\\\\\\", value, fixed = TRUE)
escaped <- gsub("\"", "\\\\\"", escaped, fixed = TRUE)
cat(sprintf(
  "{\"value\":\"%s\",\"median_ms\":%.17g}\n",
  escaped,
  median(elapsed) * 1000
))
