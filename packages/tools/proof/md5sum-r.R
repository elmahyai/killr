suppressPackageStartupMessages(library(tools))

one <- function() {
  f <- tempfile()
  writeBin(charToRaw("z\n"), f)
  miss <- tempfile()
  both <- tryCatch(md5sum(files=f, bytes=charToRaw("abc")), error=function(e) conditionMessage(e))
  rawerr <- tryCatch(md5sum(bytes="abc"), error=function(e) conditionMessage(e))
  paste0(md5sum(bytes=charToRaw("abc")), "\n", unname(md5sum(f)), "\n", unname(md5sum(miss)), "\n", both, "\n", rawerr, "\n")
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
