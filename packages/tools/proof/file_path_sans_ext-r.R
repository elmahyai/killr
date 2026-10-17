suppressPackageStartupMessages(library(tools))

one <- function() {
  show <- function(v) paste(ifelse(is.na(v), "NA", v), collapse="|")
  x <- c("file.zip", "file.tar.gz", ".hidden", "file.", "file.c++", "a.é", "a..txt", "foo/bar.txt.bak", NA)
  paste0(show(file_path_sans_ext(x)), "\n", show(file_path_sans_ext(x, TRUE)), "\n")
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
