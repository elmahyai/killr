suppressPackageStartupMessages(library(colorspace))
one <- function() list(
  coords = coords(polarLAB(c(50, 60), c(20, 30), c(10, 200))),
  matrix = coords(polarLAB(matrix(c(50, 20, 10, 60, 30, 200), ncol=3, byrow=TRUE)))
)
value <- one()
times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); one(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) * 1000 }
result <- paste(paste(capture.output(dput(value)), collapse=""), median(times), sep="\n")
writeLines(result, "packages/colorspace/docs/output/polarLAB-r.txt")
cat(result, "\n")
