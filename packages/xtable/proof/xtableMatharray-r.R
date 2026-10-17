suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

one <- function() {
  m <- matrix(c(1, 2, 3, 4, 5, 6, 7, 8), 2, 4)
  x <- xtableMatharray(m, caption = "Var", label = "eq:vcov")
  list(
    class = class(x),
    nrow = nrow(x),
    ncol = ncol(x),
    align = align(x),
    digits = digits(x),
    display = display(x),
    caption = caption(x),
    label = label(x),
    data = as.matrix(x)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = FALSE, na = "null", null = "null"))
cat("}\n")
