suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

tdata <- data.frame(
  id = c(1, 2, 2, 2, 3, 3, 3, 4, 4),
  time = c(5, 3, 8, 11, 0, 5, 9, 2, 7),
  state = factor(c(2, 2, 1, 3, 3, 1, 2, 2, 3), 1:3, c("none", "A", "B")),
  x = 1:9,
  y = 10:2
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
  serialize(survSplit(Surv2(time, state) ~ ., tdata, id = id, cut = c(2, 6, 9)))
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
