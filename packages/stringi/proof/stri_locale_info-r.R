suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


example <- stri_locale_info("pl_PL")$Name
writeLines(
  paste0("stri_locale_info('pl_PL')$Name returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_locale_info-r.txt"
)

one <- function() {
  prev <- stri_locale_get()
  on.exit(stri_locale_set(prev), add = TRUE)
  stri_locale_set("pl_PL")
  list(
    pl = stri_locale_info("pl_PL"),
    mixed = stri_locale_info("Pl_pL"),
    c = stri_locale_info("C"),
    cutf = stri_locale_info("c.UTF-8"),
    utf = stri_locale_info("en_US.UTF-8"),
    phone = stri_locale_info("fr_FR@collation=phonebook"),
    keywords = stri_locale_info("@collation=phonebook"),
    zh = stri_locale_info("zh_Hant_TW"),
    empty = stri_locale_info(""),
    null = stri_locale_info(NULL)
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
