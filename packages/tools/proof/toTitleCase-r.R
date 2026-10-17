suppressPackageStartupMessages(library(tools))

one <- function() {
  show <- function(v) paste(ifelse(is.na(v), "NA", v), collapse="|")
  x <- c("the quick brown fox", "a tale of two cities", "HTML and LaTeX", NA, "john's book", "foo-bar: baz", "\"hello\" world")
  paste0(show(toTitleCase(x)), "\n")
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
