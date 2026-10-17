library(brio)
f <- tempfile()
writeBin(charToRaw("a\r\nb\n"), f)
one <- function() file_line_endings(f)
value <- one()
times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); one(); times[i] <- as.numeric(difftime(Sys.time(), t, units = "secs")) * 1000 }
cat(sprintf('{"value":%s,"median_ms":%.9f}\n', dQuote(value), median(times)))
unlink(f)
