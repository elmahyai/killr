suppressPackageStartupMessages(library(colorspace))
f <- tempfile()
one <- function() { writehex(sRGB(c(1,0,.25), c(0,1,.5), c(0,0,.75)), f); paste(readLines(f), collapse="|") }
value <- one(); times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); one(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) * 1000 }
result <- paste(value, median(times), sep="\n")
writeLines(result, "packages/colorspace/docs/output/writehex-r.txt")
cat(result, "\n")
