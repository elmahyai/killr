suppressPackageStartupMessages(library(tools))

one <- function() {
  fail <- tryCatch(assertCondition(1 + 1, "error"), error = function(e) conditionMessage(e))
  ok <- assertCondition(stop("boom"), "error")
  msg <- capture.output(assertCondition(stop("e"), "error", verbose = TRUE), type = "message")
  paste0(fail, "\n", ok[[1]]$message, "\n", msg, "\n")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
