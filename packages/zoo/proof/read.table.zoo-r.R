.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")
canon <- function(z) {
  idx <- paste(sprintf("%.17g", as.numeric(index(z))), collapse = " ")
  vals <- paste(sprintf("%.17g", as.vector(coredata(z))), collapse = " ")
  paste0("index ", idx, "\nvalues ", vals)
}

path <- tempfile()
writeLines(c(
  "date,a,b",
  "2020-01-01,1.5,2.25",
  "2020-01-02,3.5,4.75",
  "2020-01-03,5.25,6.125"
), path)
one <- function() {
  z <- suppressWarnings(read.table.zoo(path, header = TRUE, sep = ","))
  canon(z)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
esc <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
cat(sprintf("{\"value\":\"%s\",\"median_ms\":%.17g}\n", esc(value), median(elapsed) * 1000))
