suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


path <- "/tmp/stringi-rest-proof/printf-r.txt"
dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
file.create(path)
stri_printf("%s", c("a", "b"), file = path)
shown <- paste(as.integer(readBin(path, "raw", 20)), collapse = ", ")
writeLines(
  paste0("stri_printf(\"%s\", c(\"a\", \"b\")) writes ", shown, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_printf-r.txt"
)

one <- function() {
  stri_printf("%s", c("a", "b"), file = path)
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
