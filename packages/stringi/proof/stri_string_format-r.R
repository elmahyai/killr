suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


example <- stri_string_format("%.1f", 1.25)
writeLines(
  paste0("stri_string_format('%.1f', 1.25) returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_string_format-r.txt"
)

one <- function() {
  list(
    tenth = stri_string_format("%.1f", 1.25),
    pad = stri_string_format("%05d", 7),
    na = stri_string_format("%s", NA),
    prec = stri_string_format("[%-10.3s]", "xxabcd"),
    half = stri_string_format("%.0f", c(1.5, 2.5)),
    cjk = stri_string_format("[%10s]", "一", use_length = TRUE),
    bools = stri_string_format("%s %d", TRUE, FALSE)
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
