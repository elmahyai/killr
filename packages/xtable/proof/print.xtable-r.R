suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

one <- function() {
  x <- xtable(data.frame(a = c("x&y", "z"), b = c("p", "q"), c = pi), caption = "Cap")
  list(
    latex = print(
      x,
      include.rownames = FALSE,
      print.results = FALSE,
      comment = FALSE,
      timestamp = NULL,
      floating = FALSE
    ),
    numeric = print(
      xtable(data.frame(v = c(1.2345, 1e5)), digits = c(0, 4)),
      include.rownames = FALSE,
      include.colnames = FALSE,
      print.results = FALSE,
      comment = FALSE,
      timestamp = NULL,
      floating = FALSE
    )
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
cat(toJSON(value, auto_unbox = TRUE, na = "null", null = "null"))
cat("}\n")
