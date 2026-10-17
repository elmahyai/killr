suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


example <- length(stri_locale_list())
writeLines(
  paste0("length(stri_locale_list()) returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locale_list-r.txt"
)

one <- function() stri_locale_list()

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
