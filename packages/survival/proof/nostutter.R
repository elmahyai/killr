suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

one <- function() {
  id <- c(1L, 1L, 1L, 1L, 2L, 2L, 2L, 3L, 3L)
  ev <- factor(
    c("censor", "a", "a", "b", "a", "b", "b", "censor", "b"),
    levels = c("censor", "a", "b")
  )
  y1 <- nostutter(id, ev, censor = "censor")
  xnum <- c(0L, 1L, 1L, 2L, 1L, 2L, 2L, 0L, 2L)
  y2 <- nostutter(id, xnum, censor = 0L)
  id2 <- c(1L, 1L, 1L, 2L, 2L)
  ev2 <- factor(c("a", NA, "a", "a", "b"), levels = c("censor", "a", "b"))
  y3 <- nostutter(id2, ev2, censor = "censor")
  c(
    paste(as.character(y1), collapse = ","),
    paste(as.character(y2), collapse = ","),
    paste(as.character(y3), collapse = ","),
    paste(levels(y1), collapse = "|"),
    paste(levels(y2), collapse = "|"),
    paste(levels(y3), collapse = "|")
  )
}

t0 <- as.numeric(Sys.time())
value <- one()
r_untimed <- (as.numeric(Sys.time()) - t0) * 1000

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
r_median <- median(elapsed) * 1000

cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("R_UNTIMED\n")
cat(sprintf("%.17g\n", r_untimed))
cat("R_MEDIAN\n")
cat(sprintf("%.17g\n", r_median))
