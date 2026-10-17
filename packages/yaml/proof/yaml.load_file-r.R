suppressPackageStartupMessages(library(yaml))
path <- tempfile()
writeLines(c("- hey", "- hi", "- hello"), path)
one <- function() {
  paste(yaml.load_file(path), collapse = ",")
}
ans <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(ans, "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
