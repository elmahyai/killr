suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


dir.create("/tmp/stringi-rest-proof", recursive = TRUE, showWarnings = FALSE)
path <- "/tmp/stringi-rest-proof/read-r.txt"
writeBin(charToRaw("caf\u00e9\nNA\n\n"), path)

writeLines(
  paste0("stri_read_raw(path) returns ", length(stri_read_raw(path)), " bytes."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_read_raw-r.txt"
)

one <- function() as.integer(stri_read_raw(path))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
