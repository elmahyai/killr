suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

one <- function() {
  out <- list()
  for (i in 0:7) {
    n <- 2 + (i %% 5)
    x <- xtable(data.frame(
      id = seq_len(n),
      val = seq_len(n) + i * 0.1,
      lab = letters[seq_len(n)]
    ))
    y <- autoformat(x, zap = 5 + (i %% 3))
    out[[paste0("case_", i)]] <- list(
      align = align(y),
      digits = digits(y),
      display = display(y)
    )
  }
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = FALSE, na = "null", null = "null"))
cat("}\n")
