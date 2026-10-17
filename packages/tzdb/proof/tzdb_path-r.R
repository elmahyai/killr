suppressPackageStartupMessages(library(tzdb))
invisible(tzdb_path("text"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- tzdb_path("text")
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
med <- median(elapsed)
err <- tryCatch(tzdb_path("binary"), error = function(e) conditionMessage(e))
ver <- readLines(file.path(result, "version"), warn = FALSE)
files <- sort(list.files(result), method = "radix")
cat(sprintf("r_ms %.17g\n", med * 1000))
writeLines(c(err, ver, files))
