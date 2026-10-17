library(utils)

one <- function() {
  a <- as.roman(c(0, 1, 4, 3899, NA))
  b <- as.roman(c("I", "IV", "MMMDCCCXCIX", "foo", "MMXVI"))
  paste(
    paste(as.character(a), collapse = ","),
    paste(as.character(b), collapse = ","),
    paste(as.character(as.roman(c("IV", "V")) + as.roman(c("V", "X"))), collapse = ","),
    paste(as.character(as.roman(c("IV", "V")) * 2), collapse = ","),
    paste(as.character(as.roman(c("IV", "V")) - 1), collapse = ","),
    paste(as.character(as.roman(c("IV", "V")) == as.roman(c("IV", "X"))), collapse = ","),
    sep = "\n"
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
