.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(diffobj))
a <- letters[1:6]
b <- c("b", "CC", "DD", "d", "f")
enc <- function(dat) {
  op <- as.character(dat$op)
  val <- ifelse(is.na(dat$val), "NA", dat$val)
  ida <- ifelse(is.na(dat$id.a), "NA", as.character(dat$id.a))
  idb <- ifelse(is.na(dat$id.b), "NA", as.character(dat$id.b))
  paste(op, val, ida, idb, sep = "|")
}
one <- function() ses_dat(a, b)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(enc(value), collapse = ";"), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
