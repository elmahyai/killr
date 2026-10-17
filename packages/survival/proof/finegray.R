suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

serialize <- function(d) {
  out <- c(paste(names(d), collapse = "|"))
  for (nm in names(d)) {
    col <- d[[nm]]
    if (is.factor(col)) col <- as.character(col)
    if (is.numeric(col)) {
      out <- c(out, paste(sprintf("%.17g", col), collapse = ","))
    } else {
      out <- c(out, paste(col, collapse = ","))
    }
  }
  out <- c(out, attr(d, "event"))
  out
}

one <- function() {
  fdata <- data.frame(
    time = c(1, 2, 3, 4, 4, 4, 5, 5, 6, 8, 8, 9, 10, 12),
    status = factor(
      c(1, 2, 0, 1, 0, 0, 2, 1, 0, 0, 2, 0, 1, 0),
      0:2,
      c("cen", "type1", "type2")
    ),
    x = c(5, 4, 3, 1, 2, 1, 1, 2, 2, 4, 6, 1, 2, 0),
    id = 1:14
  )
  serialize(finegray(Surv(time, status) ~ ., fdata, count = "fgcount"))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
