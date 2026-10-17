suppressPackageStartupMessages(library(survival))

serialize_ratetable <- function(rt) {
  flat <- as.vector(rt)
  isd <- attr(rt, "isDate")
  lev <- attr(rt, "levlist")
  lev_str <- vapply(
    lev,
    function(x) if (is.null(x)) "NULL" else paste(x, collapse = ";"),
    character(1)
  )
  c(
    paste(sprintf("%.17g", flat), collapse = ","),
    paste(as.integer(isd), collapse = ","),
    paste(lev_str, collapse = "|"),
    paste(colnames(rt), collapse = ",")
  )
}

one <- function() {
  d <- as.Date(c("1970-01-01", "1960-01-01", "2000-06-15"))
  rt <- ratetable(
    age = c(50, 60, 70),
    sex = factor(c("M", "F", "M"), levels = c("M", "F")),
    birth = d,
    wt = 1.5,
    entry = c(0L, 3653L, 14765L)
  )
  serialize_ratetable(rt)
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
