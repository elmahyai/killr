suppressPackageStartupMessages(library(survival))

serialize <- function(x) {
  vals <- as.numeric(x)
  c(
    paste(format(vals, digits = 17, trim = TRUE), collapse = "|"),
    paste(format(attr(x, "cutpoints"), digits = 17, trim = TRUE), collapse = "|"),
    paste(attr(x, "labels"), collapse = "|"),
    paste(levels(x), collapse = "|")
  )
}

one <- function() {
  x <- c(55, 65, 75, 85, NA, 72.5)
  a <- tcut(x, c(0, 60, 70, 80, 100), c("<=60", "60-70", "70-80", ">80"))
  b <- tcut(c(1, 2, 3, 4, 5), 3)
  cobj <- tcut(c(10, 20), c(0, 15, 30), scale = 2)
  d <- a[c(1, 3, 5, 6)]
  c(serialize(a), serialize(b), serialize(cobj), serialize(d))
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
