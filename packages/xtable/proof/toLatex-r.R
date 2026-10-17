suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

one <- function() {
  out <- list()
  x1 <- xtable(data.frame(a = 1:3, b = c(1.5, 2, 3.1), c = letters[1:3]))
  align(x1) <- c("l", "r", "r", "l")
  digits(x1) <- c(0, 0, 1, 0)
  display(x1) <- c("s", "d", "f", "s")
  out$basic <- as.character(toLatex(x1, comment = FALSE, floating = FALSE))

  x2 <- xtable(data.frame(a = 1:2, b = c(1.5, 2)))
  align(x2) <- c("r", "r", "r")
  digits(x2) <- c(0, 0, 1)
  display(x2) <- c("s", "d", "f")
  out$no_row <- as.character(
    toLatex(x2, comment = FALSE, floating = FALSE, include.rownames = FALSE)
  )

  x3 <- xtable(data.frame(x = c(0.12, 1.2), y = c("a&b", "c>d")))
  align(x3) <- c("l", "r", "l")
  digits(x3) <- c(0, 2, 0)
  display(x3) <- c("s", "f", "s")
  out$sanitize <- as.character(toLatex(x3, comment = FALSE, floating = FALSE))
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
