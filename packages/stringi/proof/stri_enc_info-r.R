.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

writeLines(
  paste0(
    'stri_enc_info("UTF-8") reports the friendly name ',
    stri_enc_info("UTF-8")$Name.friendly,
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_info-r.txt"
)
one <- function() {
  list(
    stri_enc_info("UTF-8"),
    stri_enc_info("ISO-8859-2"),
    stri_enc_info("US-ASCII"),
    stri_enc_info("UTF-16")
  )
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
