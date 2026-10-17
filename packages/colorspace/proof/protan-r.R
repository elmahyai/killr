suppressPackageStartupMessages(library(colorspace))
one <- function() protan(c("#005000", "blue", "#00BB00"), severity=.6)
value <- one(); times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); one(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) * 1000 }
result <- paste(paste(value, collapse=","), median(times), sep="\n")
writeLines(result, "packages/colorspace/docs/output/protan-r.txt")
cat(result, "\n")
