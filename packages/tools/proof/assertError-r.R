suppressPackageStartupMessages(library(tools))

one <- function() {
  fail <- tryCatch(assertError(1 + 1), error = function(e) conditionMessage(e))
  ok <- assertError(stop("boom"))
  paste0(fail, "\n", ok[[1]]$message, "\n")
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
