suppressPackageStartupMessages(library(ggplot2))
if (packageDescription("ggplot2")$Version != "4.0.3") stop("expected ggplot2 4.0.3")
options(warn = -1)
set.seed(1)
x <- rnorm(100)
one <- function() {
mean_se(x)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
nums <- as.numeric(unlist(value, use.names = FALSE))
cat(jsonlite::toJSON(list(value = nums, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
