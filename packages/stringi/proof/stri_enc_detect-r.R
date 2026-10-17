.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

eng <- paste(rep("The quick brown fox jumps over the lazy dog.", 8), collapse = " ")
guess <- stri_enc_detect(eng)[[1]]$Encoding[[1]]
writeLines(
  paste0("stri_enc_detect on the English pangram repeated eight times guesses ", guess, " first."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_enc_detect-r.txt"
)
eng <- paste(rep("The quick brown fox jumps over the lazy dog.", 8), collapse = " ")
one <- function() {
  stri_enc_detect(c(eng, "", NA_character_))
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
