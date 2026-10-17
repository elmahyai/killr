library(labeling)

output <- "packages/labeling/docs/output/extended-figures-r.png"
dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)

one <- function() {
  png(output, width = 1000, height = 1000)
  on.exit(dev.off(), add = TRUE)
  extended.figures(samples = 10)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  started <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - started
}

cat(sprintf(
  '{"value":null,"median_ms":%.17g,"output":"%s"}\n',
  median(elapsed) * 1000, output
))
