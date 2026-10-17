suppressPackageStartupMessages(library(tools))

one <- function() {
  ch <- charset_to_Unicode
  s <- apply(ch, 1, function(row) paste(row, collapse=","))
  paste0("CHAR ", nrow(ch), " ", ncol(ch), " ", paste(colnames(ch), collapse=","), " ", md5sum(bytes=charToRaw(paste(s, collapse="\n"))), "\n")
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
