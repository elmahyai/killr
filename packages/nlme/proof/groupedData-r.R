.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

one <- function() {
  df <- data.frame(
    distance = Orthodont$distance,
    age = Orthodont$age,
    Subject = as.character(Orthodont$Subject),
    Sex = as.character(Orthodont$Sex)
  )
  g <- groupedData(distance ~ age | Subject, data = df)
  h <- groupedData(distance ~ age | Sex/Subject, data = df)
  c(
    as.integer(g$Subject), g$age, g$distance,
    as.numeric(inherits(g, "nfnGroupedData")),
    as.numeric(inherits(h, "nmGroupedData")),
    as.numeric(inherits(h, "groupedData")),
    h$age, h$distance
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
