.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

one <- function() {
  a <- gsummary(Orthodont)
  b <- gsummary(Orthodont, FUN = max)
  d <- gsummary(Orthodont, invariantsOnly = TRUE)
  e <- gsummary(Orthodont, omitGroupingFactor = TRUE)
  c(
    a$distance, a$age, as.integer(a$Sex), as.integer(a$Subject),
    b$distance, b$age, as.integer(b$Sex),
    as.integer(d$Subject), as.integer(d$Sex),
    as.integer(e$Sex), e$distance, e$age
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
