suppressPackageStartupMessages(library(tools))

one <- function() {
  f <- tempfile()
  writeLines(c("foo     A description", "        continued", "", "bar\tThe bar"), f)
  idx <- read.00Index(f)
  paste0(paste(idx[,1], idx[,2], sep="=", collapse="|"), "\n")
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
