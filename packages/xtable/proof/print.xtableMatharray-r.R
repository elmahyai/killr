suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

one <- function() {
  m <- matrix(1:4, 2, 2)
  x <- xtableMatharray(m)
  print.xtableMatharray(
    x,
    print.results = FALSE,
    comment = FALSE,
    timestamp = NULL
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = TRUE))
cat("}\n")
