suppressPackageStartupMessages(library(colorspace))
one <- function() list(numeric=extract_transparency(c("#000000", "#ffffff80", NA)),
                       integer=extract_transparency(c("#000000", "#ffffff80"), "integer"),
                       character=extract_transparency(c("#000000", "#ffffff80"), "character"),
                       default=extract_transparency("#000000", default=.5))
value <- one(); times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); one(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) * 1000 }
result <- paste(paste(capture.output(dput(value)), collapse=""), median(times), sep="\n")
writeLines(result, "packages/colorspace/docs/output/extract_transparency-r.txt")
cat(result, "\n")
