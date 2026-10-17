suppressPackageStartupMessages(library(tools))

one <- function() {
  uri <- parse_URI_reference(c("https://example.com/a?q=1#f", "file", ""))
  paste0(paste(unlist(uri), collapse="|"), "\n")
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
