.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
options(warn = 1)

ex <- capture.output({
dog <- "The quick brown dog"
print(str_to_title(dog))
})
writeLines(ex, "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_to_title-r.txt")

one <- function() {
  list(
    dog = str_to_title("The quick brown dog"),
    tr = str_to_title("istanbul", "tr"),
    vec = str_to_title(c("a", NA, "")),
    empty = str_to_title(character(0))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = unbox(median(elapsed) * 1000)), auto_unbox = FALSE, na = "null", digits = 16)), "\n"))
