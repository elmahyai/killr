suppressPackageStartupMessages(library(tools))

one <- function() {
  std <- standard_package_names()
  paste0(paste(std$base, collapse=","), " || ", paste(std$recommended, collapse=","), "\n")
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
