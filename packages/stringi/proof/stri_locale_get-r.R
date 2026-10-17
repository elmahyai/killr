suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


old <- stri_locale_get()
stri_locale_set("pl_PL")
writeLines(
  paste0("stri_locale_get() returns ", stri_locale_get(), "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locale_get-r.txt"
)
stri_locale_set(old)

one <- function() {
  prev <- stri_locale_get()
  on.exit(stri_locale_set(prev), add = TRUE)
  stri_locale_set("pl_PL")
  stri_locale_get()
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
