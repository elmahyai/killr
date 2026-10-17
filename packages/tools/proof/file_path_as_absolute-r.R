suppressPackageStartupMessages(library(tools))

one <- function() {
  ok <- file_path_as_absolute("/tmp")
  bad <- tryCatch(file_path_as_absolute("no-such-assertthat-path"), error=function(e) conditionMessage(e))
  two <- tryCatch(file_path_as_absolute(c("a", "b")), error=function(e) conditionMessage(e))
  paste0(ok, "\n", bad, "\n", two, "\n")
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
