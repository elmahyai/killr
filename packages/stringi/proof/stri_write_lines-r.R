suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


dir.create("/tmp/stringi-rest-proof", recursive = TRUE, showWarnings = FALSE)
path <- "/tmp/stringi-rest-proof/write-r.txt"
file.create(path)
stri_write_lines(c("a", "b", ""), path)
writeLines(
  paste0("stri_write_lines(c(\"a\", \"b\", \"\"), path) writes ", length(readBin(path, "raw", 20)), " bytes."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_write_lines-r.txt"
)

one <- function() {
  stri_write_lines(c("a", "b", ""), path)
  invisible(NULL)
}
one()
value <- as.integer(readBin(path, "raw", 20))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
