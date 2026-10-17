suppressPackageStartupMessages(library(tools))

one <- function() {
  w <- assertWarning(warning("w"))
  err <- tryCatch(assertWarning(stop("x")), error = function(e) conditionMessage(e))
  both <- tryCatch(assertWarning({warning("w"); stop("e")}), error = function(e) conditionMessage(e))
  paste0(w[[1]]$message, "\n", err, "\n", both, "\n")
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
