.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

guess <- suppressWarnings(stri_enc_detect2("hello"))[[1]]
writeLines(
  paste0(
    'stri_enc_detect2("hello") guesses ',
    guess$Encoding[[1]],
    " with confidence ",
    guess$Confidence[[1]],
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_detect2-r.txt"
)
pl <- paste(rep("Zażółć gęślą jaźń.", 8), collapse = " ")
raw <- stri_encode(pl, to = "windows-1250", to_raw = TRUE)[[1]]
one <- function() {
  stri_enc_detect2(list(raw, raw(0)), locale = "pl")
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
