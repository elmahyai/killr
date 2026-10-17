suppressPackageStartupMessages(library(colorspace))
one <- function() { old <- whitepoint(); on.exit(whitepoint(old)); a <- whitepoint(); b <- whitepoint(100, 100, 100); c <- whitepoint(); list(a=coords(a), b=coords(b), c=coords(c)) }
value <- one(); times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); one(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) * 1000 }
result <- paste(paste(capture.output(dput(value)), collapse=""), median(times), sep="\n")
writeLines(result, "packages/colorspace/docs/output/whitepoint-r.txt")
cat(result, "\n")
