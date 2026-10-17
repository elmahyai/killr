suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

one <- function() {
  out <- logical(0)
  out <- c(out, dopb())
  op <- pboptions(type = "timer")
  out <- c(out, dopb())
  pboptions(op)
  op <- pboptions(type = "none")
  out <- c(out, dopb())
  pboptions(op)
  op <- pboptions(type = "txt")
  out <- c(out, dopb())
  pboptions(op)
  op <- pboptions(type = "shiny")
  out <- c(out, dopb())
  pboptions(op)
  op <- options(pboptions = list(type = NULL))
  out <- c(out, dopb())
  options(op)
  op <- pboptions(type = "timer")
  op2 <- options(knitr.in.progress = TRUE)
  out <- c(out, dopb())
  options(op2)
  pboptions(op)
  op <- pboptions(type = "tim")
  out <- c(out, dopb())
  pboptions(op)
  as.numeric(out)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, sprintf, character(1), fmt = "%.17g")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
