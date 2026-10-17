suppressPackageStartupMessages(library(ggplot2))
if (packageDescription("ggplot2")$Version != "4.0.3") stop("expected ggplot2 4.0.3")
options(warn = -1)
x <- 1:100
one <- function() {
cut_interval(x, 10)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = as.numeric(as.integer(value)), median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
