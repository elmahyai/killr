suppressPackageStartupMessages(library(tools))

one <- function() {
  msgs <- c(
    tryCatch(toHTML(1), error = function(e) conditionMessage(e)),
    tryCatch(toHTML("a"), error = function(e) conditionMessage(e)),
    tryCatch(toHTML(TRUE), error = function(e) conditionMessage(e)),
    tryCatch(toHTML(NULL), error = function(e) conditionMessage(e))
  )
  paste0(paste(msgs, collapse="\n"), "\n")
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
