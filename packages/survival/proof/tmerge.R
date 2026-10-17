suppressPackageStartupMessages(library(survival))

serialize_num <- function(x) {
  paste(vapply(x, function(v) if (is.na(v)) "NA" else format(v, digits = 17, trim = TRUE), ""), collapse = "|")
}

one <- function() {
  data1 <- data.frame(idd = c(1, 5, 4, 3, 2, 6), x1 = 1:6, age = 50:55)
  data2 <- data.frame(idd = c(2, 5, 1, 2, 1), x2 = 5:1, age = 48:44)
  test1 <- tmerge(data1, data1, id = idd, death = event(age))
  test2 <- tmerge(test1, data2, id = idd, zed = tdc(age, x2))
  data3 <- data.frame(
    idd = c(5, 5, 1, 1, 6, 4, 3, 2),
    age = c(45, 50, 44, 48, 53, -5, 0, 20),
    x = c(1, 5, 2, 3, 7, 4, 6, 8)
  )
  test3 <- tmerge(test2, data3, id = idd, x = cumtdc(age, x), esum = cumevent(age))
  tc <- c(t(attr(test3, "tcount")))
  c(
    serialize_num(test3$idd),
    serialize_num(test3$tstop),
    serialize_num(test3$death),
    serialize_num(test3$zed),
    serialize_num(test3$x),
    serialize_num(test3$esum),
    paste(tc, collapse = "|")
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
