
suppressPackageStartupMessages(library(tseries))
options(warn = -1)
cell <- function(v) {
  if (is.logical(v)) return(if (isTRUE(v)) "TRUE" else "FALSE")
  if (is.numeric(v)) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    return(sprintf("%.17g", v))
  }
  as.character(v)
}
join <- function(x) paste(vapply(as.vector(x), cell, ""), collapse = ",")

one <- function() {
  source("packages/tseries/proof/garch-data.R", local = TRUE)
  x <- garch_noise_200
  fit <- garch(x, order = c(1, 1), control = garch.control(trace = FALSE))
  paste(
    join(fit$coef),
    cell(fit$n.likeli),
    join(fit$residuals),
    join(fit$fitted.values),
    join(fit$vcov),
    sep = "|"
  )
}

value <- one()
if (is.null(value)) value <- "NULL"
if (!is.character(value)) value <- as.character(value)
if (length(value) != 1) value <- paste(value, collapse = ",")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sprintf("%.17g", median(elapsed) * 1000), "\n", sep = "")
