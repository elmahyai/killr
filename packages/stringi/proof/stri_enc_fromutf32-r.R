.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

shown <- stri_enc_fromutf32(c(65L, 261L))
writeLines(paste0("stri_enc_fromutf32(c(65L, 261L)) returns ", shown, "."), "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_fromutf32-r.txt")
one <- function() {
  stri_enc_fromutf32(list(
    c(65L, 261L),
    NULL,
    integer(0),
    NA_integer_,
    c(0L),
    c(0x110000L),
    c(0xD800L)
  ))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(toJSON(
  list(value = value, median_ms = unbox(median(elapsed) * 1000)),
  dataframe = "columns",
  auto_unbox = TRUE,
  na = "null",
  null = "null",
  digits = 16
))
cat("\n")
