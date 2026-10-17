suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


example <- stri_info(FALSE)$ICU.version
writeLines(
  paste0("stri_info(FALSE)$ICU.version returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_info-r.txt"
)

one <- function() {
  prev <- stri_locale_get()
  on.exit(stri_locale_set(prev), add = TRUE)
  stri_locale_set("pl_PL")
  info <- stri_info(FALSE)
  list(
    unicode = info$Unicode.version,
    icu = info$ICU.version,
    system = info$ICU.system,
    utf8 = info$ICU.UTF8,
    internal = info$Charset.internal,
    native = info$Charset.native,
    locale = info$Locale$Name,
    short = stri_info(TRUE)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
