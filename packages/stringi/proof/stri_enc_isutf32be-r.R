.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

shown <- stri_enc_isutf32be(as.raw(c(0, 0, 0, 97)))
writeLines(
  paste0("stri_enc_isutf32be(as.raw(c(0, 0, 0, 97))) returns ", ifelse(shown, "TRUE", "FALSE"), "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_isutf32be-r.txt"
)
one <- function() {
  stri_enc_isutf32be(list(as.raw(c(0, 0, 0, 97)), as.raw(c(97, 98, 99, 100)), NULL))
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
