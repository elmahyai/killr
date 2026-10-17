.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

previous <- suppressWarnings(stri_enc_set("ISO-8859-2"))
suppressWarnings(stri_enc_set(previous))
writeLines(
  paste0(
    'stri_enc_set("ISO-8859-2") returns ',
    previous,
    " because this ICU build keeps the default charset locked."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_set-r.txt"
)
one <- function() {
  previous <- stri_enc_set("ISO-8859-2")
  after <- stri_enc_get()
  stri_enc_set(previous)
  c(previous, after)
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
