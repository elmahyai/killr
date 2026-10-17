.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  fmt <- function(v) if (is.na(v)) "NA" else sprintf("%.16g", as.numeric(v))
  if (is.null(x)) return(character(0))
  paste(vapply(as.numeric(x), fmt, ""), collapse = ",")
}

one <- function() {
  val3899 <- "MMMDCCCXCIX"
  val3900 <- "MMMCM"
  val4000 <- "MMMM"
  c(
    flat(roman2int(c("I", "V", "X", "C", "L", "D", "M"))),
    flat(roman2int("MMXVI")),
    flat(roman2int("mmxvi")),
    flat(roman2int(val3899)),
    flat(roman2int(val3900)),
    flat(roman2int(val4000)),
    flat(roman2int(c("  iv  ", "MCMLXXXIV", "invalid", "", NA, "IXX"))),
    flat(roman2int(c("CDXLIV", "CMXCIX", "MMCDXLIV")))
  )
}

value <- paste(one(), collapse = ",")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', value, median(elapsed) * 1000))
