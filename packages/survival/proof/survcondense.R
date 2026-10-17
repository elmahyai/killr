suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

aml <- data.frame(
  time = c(
    9, 13, 13, 18, 23, 28, 31, 34, 45, 48, 161, 5, 5, 8, 8, 12, 16, 23, 27, 30, 33, 43, 45
  ),
  status = c(
    1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1
  ),
  x = c(
    rep("Maintained", 11), rep("Nonmaintained", 12)
  ),
  stringsAsFactors = FALSE
)

serialize <- function(cdata) {
  out <- c(paste(names(cdata), collapse = "|"))
  for (nm in names(cdata)) {
    col <- cdata[[nm]]
    if (is.factor(col)) col <- as.character(col)
    if (is.numeric(col)) {
      out <- c(out, paste(sprintf("%.17g", col), collapse = ","))
    } else {
      out <- c(out, paste(col, collapse = ","))
    }
  }
  out
}

one <- function() {
  test1 <- survSplit(Surv(time, status) ~ ., data = aml, cut = c(10, 20, 30), id = "newid")
  test2 <- survcondense(Surv(tstart, time, status) ~ x, test1, id = newid)
  serialize(test2)
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
