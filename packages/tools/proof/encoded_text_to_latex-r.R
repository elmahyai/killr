suppressPackageStartupMessages(library(tools))

one <- function() {
  paste0(encoded_text_to_latex("A caf\u00e9", "UTF-8"), "\n", encoded_text_to_latex("A", "latin1"), "\n")
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
